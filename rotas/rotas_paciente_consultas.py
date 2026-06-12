"""
CardioLab - rotas de consultas do paciente.
Agendamento, confirmação, remarcação e cancelamento.
"""

import logging
from datetime import datetime, timedelta

from flask import current_app, flash, jsonify, redirect, request, session, url_for

from extensoes import obter_banco
from servicos.agenda import (
    consulta_no_futuro,
    encontrar_conflito_de_agenda,
    horario_dentro_do_expediente,
    normalizar_horario,
)
from servicos.formatacao import formatar_data_br
from servicos.carteirinha import (
    buscar_carteirinha_paciente,
    garantir_schema_carteirinha,
)
from rotas.rotas_paciente import rotas_paciente, paciente_obrigatorio, obter_paciente_id


logger = logging.getLogger(__name__)


@rotas_paciente.route("/consultas")
@paciente_obrigatorio
def consultas():
    """Redireciona o atalho de consultas para a aba correspondente do painel."""

    return redirect(url_for("paciente.painel"))


@rotas_paciente.route("/consultas/nova", methods=["GET", "POST"])
@paciente_obrigatorio
def nova_consulta():
    """Valida agenda, conflito e horário futuro antes de criar uma consulta."""

    if request.method == "GET":
        return redirect(url_for("paciente.painel"))

    usuario = session["usuario"]
    db = obter_banco()
    garantir_schema_carteirinha(db)
    cursor = db.cursor()
    paciente_id = obter_paciente_id(usuario["id"])

    medico_id = request.form.get("medico_id")
    servico_id = request.form.get("servico_id")
    data_consulta = request.form.get("data_consulta")
    horario_consulta = request.form.get("horario_consulta")
    entrar_lista_espera = request.form.get("entrar_lista_espera")

    if not all([medico_id, servico_id, data_consulta, horario_consulta]):
        flash("Preencha todos os campos.", "perigo")
        cursor.close()
        return redirect(url_for("paciente.painel"))

    try:
        if not consulta_no_futuro(data_consulta, horario_consulta):
            flash("Escolha uma data e horário futuros para agendar.", "perigo")
            cursor.close()
            return redirect(url_for("paciente.painel", aba="consultas"))
    except ValueError:
        flash("Data ou horário inválido.", "perigo")
        cursor.close()
        return redirect(url_for("paciente.painel", aba="consultas"))

    cursor.execute(
        """
        SELECT id, nome, descricao, preparo, duracao_minutos, indicacao
        FROM servicos
        WHERE id = %s
        """,
        (servico_id,),
    )
    servico = cursor.fetchone()
    duracao = servico["duracao_minutos"] if servico else 30

    cursor.execute("SELECT expediente_inicio, expediente_fim FROM medicos WHERE id = %s", (medico_id,))
    medico = cursor.fetchone()
    if not medico or not horario_dentro_do_expediente(horario_consulta, duracao, medico["expediente_inicio"], medico["expediente_fim"]):
        flash("Horário fora do expediente do médico.", "perigo")
        cursor.close()
        return redirect(url_for("paciente.painel"))

    conflito = encontrar_conflito_consulta(cursor, medico_id, paciente_id, data_consulta, horario_consulta, duracao)
    if conflito:
        if entrar_lista_espera:
            cursor.execute(
                """
                INSERT INTO lista_espera (paciente_id, medico_id, servico_id, data_desejada, horario_desejado, situacao)
                VALUES (%s, %s, %s, %s, %s, 'aguardando')
                """,
                (paciente_id, medico_id, servico_id, data_consulta, horario_consulta),
            )
            db.commit()
            flash("Horário indisponível. Você entrou na lista de espera.", "informacao")
        else:
            flash("Horário indisponível. Escolha outro horário ou entre na lista de espera.", "perigo")
        cursor.close()
        return redirect(url_for("paciente.painel", aba="consultas"))

    try:
        cursor.execute(
            """
            INSERT INTO consultas
                (paciente_id, medico_id, servico_id, data_consulta, horario_consulta, duracao_minutos, situacao)
            VALUES (%s, %s, %s, %s, %s, %s, 'agendada')
            """,
            (paciente_id, medico_id, servico_id, data_consulta, horario_consulta, duracao),
        )
        consulta_id = cursor.lastrowid
        if servico and "teleconsulta" in servico["nome"].lower():
            cursor.execute(
                "UPDATE consultas SET sala_teleconsulta_url = %s WHERE id = %s",
                (f"https://meet.jit.si/cardiolab-{consulta_id}", consulta_id),
            )
        carteirinha = buscar_carteirinha_paciente(cursor, paciente_id)
        observacao_carteirinha = ""
        if carteirinha and carteirinha.get("situacao") == "ativa":
            observacao_carteirinha = f" Benefício CardioLab Care aplicado: {carteirinha.get('desconto_consulta_percentual') or 0}% em consultas."

        cursor.execute(
            """
            INSERT INTO notificacoes (usuario_id, titulo, mensagem, tipo)
            VALUES (%s, 'Consulta Agendada', %s, 'sucesso')
            """,
            (usuario["id"], f"Sua consulta foi agendada para {formatar_data_br(data_consulta)} às {horario_consulta}.{observacao_carteirinha}"),
        )
        db.commit()
        flash("Consulta agendada com sucesso. Use o botão de WhatsApp no cartão para confirmar.", "sucesso")
    except Exception:
        db.rollback()
        logger.exception("criacao_consulta_falhou", extra={"extra": {"paciente_id": paciente_id}})
        flash("Erro ao agendar consulta. Tente novamente.", "perigo")
    finally:
        cursor.close()

    return redirect(url_for("paciente.painel", aba="consultas"))


def encontrar_conflito_consulta(cursor, medico_id, paciente_id, data_consulta, horario_consulta, duracao):
    """Busca conflitos do médico e do paciente para impedir dupla marcação."""

    cursor.execute(
        """
        SELECT id, horario_consulta, duracao_minutos, 'medico' as dono_conflito
        FROM consultas
        WHERE medico_id = %s AND data_consulta = %s
          AND situacao IN ('agendada', 'confirmada', 'em_atendimento')
        UNION ALL
        SELECT id, horario_consulta, duracao_minutos, 'paciente' as dono_conflito
        FROM consultas
        WHERE paciente_id = %s AND data_consulta = %s
          AND situacao IN ('agendada', 'confirmada', 'em_atendimento')
        """,
        (medico_id, data_consulta, paciente_id, data_consulta),
    )
    consultas_existentes = cursor.fetchall()
    return encontrar_conflito_de_agenda(consultas_existentes, horario_consulta, duracao)


@rotas_paciente.route("/consultas/<int:consulta_id>/confirmar", methods=["POST"])
@paciente_obrigatorio
def confirmar_consulta(consulta_id):
    """Confirma presença do paciente em uma consulta ainda agendada."""

    usuario = session["usuario"]
    db = obter_banco()
    cursor = db.cursor()
    paciente_id = obter_paciente_id(usuario["id"])
    cursor.execute(
        """
        UPDATE consultas
        SET situacao = 'confirmada', confirmada_em = NOW()
        WHERE id = %s AND paciente_id = %s AND situacao = 'agendada'
        """,
        (consulta_id, paciente_id),
    )
    db.commit()
    cursor.close()
    flash("Presença confirmada.", "sucesso")
    return redirect(url_for("paciente.painel"))


@rotas_paciente.route("/consultas/<int:consulta_id>/remarcar", methods=["POST"])
@paciente_obrigatorio
def remarcar_consulta(consulta_id):
    """Remarca consulta existente apenas para horários futuros e disponíveis."""

    usuario = session["usuario"]
    db = obter_banco()
    cursor = db.cursor()
    paciente_id = obter_paciente_id(usuario["id"])
    nova_data = request.form.get("data_consulta")
    novo_horario = request.form.get("horario_consulta")

    if not all([nova_data, novo_horario]):
        flash("Informe nova data e novo horário.", "perigo")
        cursor.close()
        return redirect(url_for("paciente.painel", aba="consultas"))

    try:
        if not consulta_no_futuro(nova_data, novo_horario):
            flash("Não é possível remarcar para uma data ou horário que já passou.", "perigo")
            cursor.close()
            return redirect(url_for("paciente.painel", aba="consultas"))
    except ValueError:
        flash("Data ou horário inválido para remarcação.", "perigo")
        cursor.close()
        return redirect(url_for("paciente.painel", aba="consultas"))

    cursor.execute(
        """
        SELECT a.*, s.duracao_minutos
        FROM consultas a
        JOIN servicos s ON a.servico_id = s.id
        WHERE a.id = %s AND a.paciente_id = %s AND a.situacao IN ('agendada', 'confirmada')
        """,
        (consulta_id, paciente_id),
    )
    consulta = cursor.fetchone()
    if not consulta:
        flash("Consulta não encontrada.", "perigo")
        cursor.close()
        return redirect(url_for("paciente.painel", aba="consultas"))

    cursor.execute("SELECT expediente_inicio, expediente_fim FROM medicos WHERE id = %s", (consulta["medico_id"],))
    medico = cursor.fetchone()
    if not medico or not horario_dentro_do_expediente(novo_horario, consulta["duracao_minutos"], medico["expediente_inicio"], medico["expediente_fim"]):
        flash("Novo horário fora do expediente do médico.", "perigo")
        cursor.close()
        return redirect(url_for("paciente.painel", aba="consultas"))

    conflito = encontrar_conflito_consulta(
        cursor,
        consulta["medico_id"],
        paciente_id,
        nova_data,
        novo_horario,
        consulta["duracao_minutos"],
    )
    if conflito and conflito["id"] != consulta_id:
        flash("Novo horário indisponível.", "perigo")
        cursor.close()
        return redirect(url_for("paciente.painel", aba="consultas"))

    cursor.execute(
        """
        UPDATE consultas
        SET data_consulta = %s, horario_consulta = %s, situacao = 'agendada'
        WHERE id = %s
        """,
        (nova_data, novo_horario, consulta_id),
    )
    cursor.execute(
        """
        INSERT INTO notificacoes (usuario_id, titulo, mensagem, tipo)
        VALUES (%s, 'Consulta Reagendada', %s, 'informacao')
        """,
        (usuario["id"], f"Sua consulta foi reagendada para {formatar_data_br(nova_data)} às {novo_horario}."),
    )
    db.commit()
    cursor.close()
    flash("Consulta reagendada com sucesso.", "sucesso")
    return redirect(url_for("paciente.painel", aba="consultas"))


@rotas_paciente.route("/consultas/<int:consulta_id>/cancelar", methods=["POST"])
@paciente_obrigatorio
def cancelar_consulta(consulta_id):
    """Cancela consulta respeitando antecedência mínima e avisa lista de espera."""

    usuario = session["usuario"]
    db = obter_banco()
    cursor = db.cursor()
    paciente_id = obter_paciente_id(usuario["id"])

    cursor.execute(
        """
        SELECT * FROM consultas
        WHERE id = %s AND paciente_id = %s AND situacao IN ('agendada', 'confirmada')
        """,
        (consulta_id, paciente_id),
    )
    consulta = cursor.fetchone()
    if not consulta:
        flash("Consulta não encontrada ou não pode ser cancelada.", "perigo")
        cursor.close()
        return redirect(url_for("paciente.painel"))

    data_hora_consulta = datetime.combine(consulta["data_consulta"], normalizar_horario(consulta["horario_consulta"]))
    if datetime.now() + timedelta(hours=current_app.config["HORAS_MINIMAS_CANCELAMENTO"]) > data_hora_consulta:
        flash(f"Cancelamento permitido apenas com {current_app.config['HORAS_MINIMAS_CANCELAMENTO']}h de antecedência.", "perigo")
        cursor.close()
        return redirect(url_for("paciente.painel"))

    motivo = request.form.get("motivo", "Cancelado pelo paciente")
    cursor.execute(
        "UPDATE consultas SET situacao = 'cancelada', motivo_cancelamento = %s WHERE id = %s",
        (motivo, consulta_id),
    )
    notificar_lista_espera_vaga(cursor, consulta)
    db.commit()
    cursor.close()
    flash("Consulta cancelada com sucesso.", "sucesso")
    return redirect(url_for("paciente.painel"))


def notificar_lista_espera_vaga(cursor, consulta):
    """Notifica o primeiro paciente da lista quando uma vaga é liberada."""

    cursor.execute(
        """
        SELECT w.*, p.usuario_id
        FROM lista_espera w
        JOIN pacientes p ON w.paciente_id = p.id
        WHERE w.medico_id = %s AND w.servico_id = %s
          AND w.data_desejada = %s AND w.situacao = 'aguardando'
        ORDER BY w.criado_em
        LIMIT 1
        """,
        (consulta["medico_id"], consulta["servico_id"], consulta["data_consulta"]),
    )
    waitlist = cursor.fetchone()
    if waitlist:
        cursor.execute(
            """
            INSERT INTO notificacoes (usuario_id, titulo, mensagem, tipo)
            VALUES (%s, 'Horário disponível', 'Uma vaga abriu para o exame desejado. Acesse o portal para agendar.', 'sucesso')
            """,
            (waitlist["usuario_id"],),
        )
        cursor.execute("UPDATE lista_espera SET situacao = 'notificado' WHERE id = %s", (waitlist["id"],))
