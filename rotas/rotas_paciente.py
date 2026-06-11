"""
CardioLab - rotas do paciente.
Painel, consultas, exames, saúde, risco cardíaco e notificações.
"""

import json
import logging
import time
from datetime import date, datetime, timedelta

from flask import Blueprint, Response, abort, current_app, flash, jsonify, redirect, render_template, request, send_file, session, stream_with_context, url_for
from functools import wraps

from extensoes import obter_banco
from servicos.agenda import (
    bloquear_horarios_passados,
    consulta_no_futuro,
    encontrar_conflito_de_agenda,
    horario_dentro_do_expediente,
    montar_horarios_disponiveis,
    montar_link_whatsapp_confirmacao,
    normalizar_horario,
)
from servicos.formatacao import dia_semana_curto, formatar_data_br, formatar_data_curta, formatar_data_hora_curta, formatar_horario
from servicos.carteirinha import (
    buscar_carteirinha_paciente,
    garantir_schema_carteirinha,
    listar_planos_carteirinha,
    solicitar_carteirinha,
)
from servicos.fotos import salvar_foto_perfil
from servicos.conteudo_publico import completar_fotos_medicos
from servicos.risco import calcular_risco_framingham, idade_pela_data_nascimento
from servicos.exames import (
    buscar_exame_paciente,
    criar_token_compartilhamento,
    gerar_pdf_com_marca_dagua,
    listar_exames_paciente,
    montar_visualizacao_exame,
    nome_download_exame,
    resolver_caminho_arquivo_exame,
)


rotas_paciente = Blueprint("paciente", __name__, url_prefix="/paciente")
logger = logging.getLogger(__name__)


def paciente_obrigatorio(f):
    """Protege rotas usadas por pacientes e administradores autenticados."""

    @wraps(f)
    def decorated(*args, **kwargs):
        """Valida sessão e perfil antes de executar a rota do paciente."""

        if "usuario" not in session:
            flash("Faça login para acessar esta página.", "atencao")
            return redirect(url_for("autenticacao.entrar"))
        if session["usuario"]["perfil"] not in ("paciente", "administrador"):
            flash("Acesso restrito a pacientes.", "perigo")
            return redirect(url_for("publico.inicio"))
        return f(*args, **kwargs)

    return decorated


def obter_paciente_id(usuario_id):
    """Localiza o cadastro de paciente ligado ao usuário logado."""

    db = obter_banco()
    garantir_schema_carteirinha(db)
    cursor = db.cursor()
    cursor.execute("SELECT id FROM pacientes WHERE usuario_id = %s", (usuario_id,))
    result = cursor.fetchone()
    cursor.close()
    return result["id"] if result else None


def saudacao_atual():
    """Escolhe a saudação do painel conforme o horário atual."""

    hour = datetime.now().hour
    if hour < 12:
        return "Bom dia"
    if hour < 18:
        return "Boa tarde"
    return "Boa noite"


@rotas_paciente.route("/painel")
@paciente_obrigatorio
def painel():
    """Monta o painel do paciente com consultas, exames, saúde, notificações e carteirinha."""

    usuario = session["usuario"]
    db = obter_banco()
    cursor = db.cursor()

    paciente_id = obter_paciente_id(usuario["id"])
    if not paciente_id:
        flash("Perfil de paciente não encontrado.", "perigo")
        return redirect(url_for("publico.inicio"))

    cursor.execute(
        """
        SELECT p.*, u.nome, u.email, u.cpf, u.foto_perfil
        FROM pacientes p
        JOIN usuarios u ON p.usuario_id = u.id
        WHERE p.id = %s
        """,
        (paciente_id,),
    )
    paciente = cursor.fetchone()

    cursor.execute(
        """
        SELECT a.*, s.nome as nome_servico, s.preparo,
               u.nome as nome_medico, d.especialidade
        FROM consultas a
        JOIN servicos s ON a.servico_id = s.id
        JOIN medicos d ON a.medico_id = d.id
        JOIN usuarios u ON d.usuario_id = u.id
        WHERE a.paciente_id = %s
          AND (
              a.data_consulta > CURDATE()
              OR (a.data_consulta = CURDATE() AND a.horario_consulta >= CURTIME())
          )
          AND a.situacao IN ('agendada', 'confirmada')
        ORDER BY a.data_consulta, a.horario_consulta
        LIMIT 5
        """,
        (paciente_id,),
    )
    proximas_consultas = cursor.fetchall()

    for consulta in proximas_consultas:
        consulta["rotulo_horario"] = formatar_horario(normalizar_horario(consulta["horario_consulta"]))
        consulta["contagem_iso"] = datetime.combine(
            consulta["data_consulta"],
            normalizar_horario(consulta["horario_consulta"]),
        ).isoformat()
        consulta["link_whatsapp"] = montar_link_whatsapp_confirmacao(
            current_app.config["NUMERO_WHATSAPP"],
            consulta,
            consulta.get("nome_servico"),
            consulta.get("nome_medico"),
        )
        if "teleconsulta" in (consulta.get("nome_servico") or "").lower():
            consulta["url_teleconsulta"] = consulta.get("sala_teleconsulta_url") or (
                f"https://meet.jit.si/cardiolab-{consulta['id']}"
            )
            consulta["url_espera_teleconsulta"] = url_for("paciente.sala_espera_teleconsulta", consulta_id=consulta["id"])

    cursor.execute(
        """
        SELECT a.*, s.nome as nome_servico, u.nome as nome_medico, d.especialidade
        FROM consultas a
        JOIN servicos s ON a.servico_id = s.id
        JOIN medicos d ON a.medico_id = d.id
        JOIN usuarios u ON d.usuario_id = u.id
        WHERE a.paciente_id = %s
          AND (
              a.data_consulta < CURDATE()
              OR (a.data_consulta = CURDATE() AND a.horario_consulta < CURTIME())
              OR a.situacao = 'finalizada'
          )
        ORDER BY a.data_consulta DESC
        LIMIT 10
        """,
        (paciente_id,),
    )
    consultas_passadas = cursor.fetchall()

    exames = listar_exames_paciente(cursor, paciente_id)

    cursor.execute(
        """
        SELECT * FROM metricas_saude
        WHERE paciente_id = %s
        ORDER BY medido_em DESC
        LIMIT 12
        """,
        (paciente_id,),
    )
    metricas_saude = cursor.fetchall()

    cursor.execute(
        """
        SELECT * FROM notificacoes
        WHERE usuario_id = %s AND lida = 0
        ORDER BY criado_em DESC
        LIMIT 10
        """,
        (usuario["id"],),
    )
    notificacoes = cursor.fetchall()

    cursor.execute(
        """
        SELECT mr.*, u.nome as nome_medico
        FROM prontuarios mr
        JOIN medicos d ON mr.medico_id = d.id
        JOIN usuarios u ON d.usuario_id = u.id
        WHERE mr.paciente_id = %s
        ORDER BY mr.criado_em DESC
        LIMIT 1
        """,
        (paciente_id,),
    )
    prontuario = cursor.fetchone()

    cursor.execute(
        """
        SELECT d.id, d.especialidade, d.crm, d.biografia, d.expediente_inicio, d.expediente_fim,
               u.nome, u.email, u.foto_perfil
        FROM medicos d
        JOIN usuarios u ON d.usuario_id = u.id
        WHERE u.ativo = 1
        ORDER BY u.nome
        """
    )
    medicos = completar_fotos_medicos(cursor.fetchall())

    cursor.execute(
        """
        SELECT id, nome, descricao, preparo, duracao_minutos, indicacao
        FROM servicos
        ORDER BY nome
        """
    )
    servicos = cursor.fetchall()

    cursor.execute(
        "SELECT COUNT(*) as total FROM consultas WHERE paciente_id = %s AND situacao = 'finalizada'",
        (paciente_id,),
    )
    total_concluidas = cursor.fetchone()["total"]

    cursor.execute(
        """
        SELECT * FROM calculos_risco
        WHERE paciente_id = %s
        ORDER BY calculado_em DESC
        LIMIT 5
        """,
        (paciente_id,),
    )
    historico_risco = cursor.fetchall()

    resumo_risco = historico_risco[0] if historico_risco else estimar_risco_paciente(paciente, metricas_saude)
    linha_tempo = montar_linha_tempo_paciente(proximas_consultas, consultas_passadas, exames, metricas_saude)
    carteirinha = buscar_carteirinha_paciente(cursor, paciente_id)
    planos_carteirinha = listar_planos_carteirinha(cursor)
    cursor.close()

    return render_template(
        "painel_paciente.html",
        paciente=paciente,
        usuario_atual=session.get("usuario"),
        proximas_consultas=proximas_consultas,
        consultas_passadas=consultas_passadas,
        exames=exames,
        metricas_saude=metricas_saude,
        notificacoes=notificacoes,
        prontuario=prontuario,
        medicos=medicos,
        servicos=servicos,
        mostrar_formulario_consulta=True,
        saudacao=saudacao_atual(),
        total_concluidas=total_concluidas,
        resumo_risco=resumo_risco,
        historico_risco=historico_risco,
        linha_tempo=linha_tempo,
        carteirinha=carteirinha,
        planos_carteirinha=planos_carteirinha,
    )


def estimar_risco_paciente(paciente, metricas_saude):
    """Estima risco cardiovascular inicial usando os últimos sinais de saúde disponíveis."""

    ultima_metrica = metricas_saude[0] if metricas_saude else {}
    idade = idade_pela_data_nascimento(paciente.get("data_nascimento")) if paciente else None
    if not idade or idade < 30 or idade > 74:
        return {"risco_percentual": 0, "classe_risco": "baixo", "media_populacional_percentual": 0}

    pressao_sistolica = 120
    if ultima_metrica.get("pressao_arterial"):
        pressao_sistolica = int(str(ultima_metrica["pressao_arterial"]).split("/")[0])

    return calcular_risco_framingham(
        sexo="F",
        idade=idade,
        colesterol_total=float(ultima_metrica.get("colesterol") or 190),
        hdl=50,
        pressao_sistolica=pressao_sistolica,
        trata_pressao=True,
        fumante=False,
        diabetes=bool(ultima_metrica.get("glicemia") and float(ultima_metrica["glicemia"]) >= 126),
    )


def montar_linha_tempo_paciente(proximas_consultas, consultas_passadas, exames, metricas):
    """Combina consultas, exames e métricas em uma linha do tempo única."""

    eventos = []
    for consulta in proximas_consultas[:3]:
        eventos.append({
            "tipo": "Consulta",
            "classe": "consulta",
            "titulo": consulta["nome_servico"],
            "data": consulta["data_consulta"],
            "situacao": consulta["situacao"],
        })
    for consulta in consultas_passadas[:3]:
        eventos.append({
            "tipo": "Histórico",
            "classe": "historico",
            "titulo": consulta["nome_servico"],
            "data": consulta["data_consulta"],
            "situacao": consulta["situacao"],
        })
    for exame in exames[:3]:
        eventos.append({
            "tipo": "Exame",
            "classe": "exame",
            "titulo": exame["titulo"],
            "data": exame["criado_em"],
            "situacao": "novo",
        })
    for metrica in metricas[:2]:
        eventos.append({
            "tipo": "Saúde",
            "classe": "saude",
            "titulo": "Sinais vitais registrados",
            "data": metrica["medido_em"],
            "situacao": "ok",
        })

    linha_tempo = sorted(eventos, key=lambda item: chave_ordenacao_linha_tempo(item["data"]), reverse=True)[:8]
    for item in linha_tempo:
        item["rotulo_data"] = rotulo_data_linha_tempo(item["data"])
        item["rotulo_situacao"] = str(item.get("situacao") or "").replace("_", " ").capitalize()
    return linha_tempo


def chave_ordenacao_linha_tempo(value):
    """Normaliza datas da linha do tempo para permitir ordenação consistente."""

    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())
    return datetime.min


def rotulo_data_linha_tempo(value):
    """Formata a data da linha do tempo de acordo com o nivel de detalhe disponivel."""

    if isinstance(value, datetime):
        return formatar_data_hora_curta(value)
    if isinstance(value, date):
        return formatar_data_curta(value)
    if value:
        value_text = str(value)
        return formatar_data_hora_curta(value_text) if len(value_text) > 10 else formatar_data_curta(value_text)
    return "-"


@rotas_paciente.route("/perfil/foto", methods=["POST"])
@paciente_obrigatorio
def atualizar_foto_perfil():
    """Salva nova foto do paciente e atualiza a sessão usada no cabeçalho."""

    usuario = session["usuario"]
    try:
        url_foto = salvar_foto_perfil(
            request.files.get("foto_perfil"),
            current_app.config["PASTA_ARQUIVOS"],
            usuario["id"],
        )
        db = obter_banco()
        cursor = db.cursor()
        cursor.execute("UPDATE usuarios SET foto_perfil = %s WHERE id = %s", (url_foto, usuario["id"]))
        db.commit()
        cursor.close()
        session["usuario"]["foto_perfil"] = url_foto
        flash("Foto atualizada com sucesso.", "sucesso")
    except ValueError as erro:
        flash(str(erro), "perigo")
    except Exception:
        logger.exception("atualizacao_foto_paciente_falhou", extra={"extra": {"usuario_id": usuario["id"]}})
        flash("Não foi possível atualizar sua foto agora.", "perigo")
    return redirect(url_for("paciente.painel"))


@rotas_paciente.route("/carteirinha/solicitar", methods=["POST"])
@paciente_obrigatorio
def solicitar_plano_carteirinha():
    """Solicita uma carteirinha CardioLab Care e registra notificação de análise."""

    usuario = session["usuario"]
    db = obter_banco()
    paciente_id = obter_paciente_id(usuario["id"])
    plano_id = request.form.get("plano_id")
    if not paciente_id or not plano_id:
        flash("Selecione um plano CardioLab Care.", "perigo")
        return redirect(url_for("paciente.painel", aba="carteirinha"))

    cursor = None
    try:
        carteirinha_solicitada, erro = solicitar_carteirinha(db, paciente_id, plano_id, usuario.get("nome"))
        if erro:
            flash(erro, "atencao")
        else:
            cursor = db.cursor()
            cursor.execute(
                """
                INSERT INTO notificacoes (usuario_id, titulo, mensagem, tipo)
                VALUES (%s, 'Carteirinha em análise', %s, 'informacao')
                """,
                (
                    usuario["id"],
                    f"Sua solicitação {carteirinha_solicitada['numero_carteirinha']} foi enviada para validação administrativa.",
                ),
            )
            db.commit()
            flash("Solicitação enviada. A carteirinha fica pendente até validação da recepção.", "sucesso")
    except Exception:
        db.rollback()
        logger.exception("solicitacao_carteirinha_falhou", extra={"extra": {"paciente_id": paciente_id}})
        flash("Não foi possível solicitar a carteirinha agora.", "perigo")
    finally:
        if cursor:
            cursor.close()
    return redirect(url_for("paciente.painel", aba="carteirinha"))


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


@rotas_paciente.route("/api/disponibilidade")
@paciente_obrigatorio
def api_disponibilidade():
    """Retorna horários livres e ocupados para médico, serviço e data escolhidos."""

    medico_id = request.args.get("medico_id")
    servico_id = request.args.get("servico_id")
    data_selecionada = request.args.get("data")
    if not all([medico_id, servico_id, data_selecionada]):
        return jsonify({"horarios": []})

    db = obter_banco()
    cursor = db.cursor()
    cursor.execute("SELECT expediente_inicio, expediente_fim FROM medicos WHERE id = %s", (medico_id,))
    medico = cursor.fetchone()
    cursor.execute("SELECT duracao_minutos FROM servicos WHERE id = %s", (servico_id,))
    servico = cursor.fetchone()
    cursor.execute(
        """
        SELECT horario_consulta, duracao_minutos
        FROM consultas
        WHERE medico_id = %s AND data_consulta = %s AND situacao IN ('agendada', 'confirmada', 'em_atendimento')
        """,
        (medico_id, data_selecionada),
    )
    ocupadas = cursor.fetchall()
    cursor.close()
    if not medico or not servico:
        return jsonify({"horarios": []})
    horarios = montar_horarios_disponiveis(medico["expediente_inicio"], medico["expediente_fim"], servico["duracao_minutos"], ocupadas)
    return jsonify({"horarios": bloquear_horarios_passados(horarios, data_selecionada)})


@rotas_paciente.route("/api/disponibilidade-calendario")
@paciente_obrigatorio
def api_disponibilidade_calendario():
    """Calcula disponibilidade resumida dos próximos dias para o calendário."""

    medico_id = request.args.get("medico_id")
    servico_id = request.args.get("servico_id")
    if not all([medico_id, servico_id]):
        return jsonify({"dias": []})

    db = obter_banco()
    cursor = db.cursor()
    cursor.execute("SELECT expediente_inicio, expediente_fim FROM medicos WHERE id = %s", (medico_id,))
    medico = cursor.fetchone()
    cursor.execute("SELECT duracao_minutos FROM servicos WHERE id = %s", (servico_id,))
    servico = cursor.fetchone()
    if not medico or not servico:
        cursor.close()
        return jsonify({"dias": []})

    dias = []
    for delta in range(21):
        dia = date.today() + timedelta(days=delta)
        cursor.execute(
            """
            SELECT horario_consulta, duracao_minutos
            FROM consultas
            WHERE medico_id = %s AND data_consulta = %s
              AND situacao IN ('agendada', 'confirmada', 'em_atendimento')
            """,
            (medico_id, dia),
        )
        ocupadas = cursor.fetchall()
        horarios = bloquear_horarios_passados(
            montar_horarios_disponiveis(medico["expediente_inicio"], medico["expediente_fim"], servico["duracao_minutos"], ocupadas),
            dia,
        )
        vagas_livres = sum(1 for horario in horarios if horario["disponivel"])
        dias.append(
            {
                "data": dia.isoformat(),
                "rotulo": formatar_data_curta(dia),
                "dia_semana": dia_semana_curto(dia),
                "vagas_livres": vagas_livres,
                "situacao": "disponivel" if vagas_livres else "lotado",
            }
        )
    cursor.close()
    return jsonify({"dias": dias})


@rotas_paciente.route("/api/sugerir-medico")
@paciente_obrigatorio
def api_sugerir_medico():
    """Sugere o médico com mais horários livres para o serviço selecionado."""

    servico_id = request.args.get("servico_id")
    if not servico_id:
        return jsonify({"medico": None})

    db = obter_banco()
    cursor = db.cursor()
    cursor.execute("SELECT duracao_minutos FROM servicos WHERE id = %s", (servico_id,))
    servico = cursor.fetchone()
    cursor.execute(
        """
        SELECT d.id, d.expediente_inicio, d.expediente_fim, u.nome, d.especialidade
        FROM medicos d
        JOIN usuarios u ON d.usuario_id = u.id
        WHERE u.ativo = 1
        """
    )
    medicos = cursor.fetchall()
    duracao = servico["duracao_minutos"] if servico else 30
    melhor = None
    for medico in medicos:
        vagas_livres = 0
        for delta in range(7):
            dia = date.today() + timedelta(days=delta)
            cursor.execute(
                """
                SELECT horario_consulta, duracao_minutos
                FROM consultas
                WHERE medico_id = %s AND data_consulta = %s
                  AND situacao IN ('agendada', 'confirmada', 'em_atendimento')
                """,
                (medico["id"], dia),
            )
            ocupadas = cursor.fetchall()
            horarios = bloquear_horarios_passados(
                montar_horarios_disponiveis(medico["expediente_inicio"], medico["expediente_fim"], duracao, ocupadas),
                dia,
            )
            vagas_livres += sum(1 for horario in horarios if horario["disponivel"])
        if melhor is None or vagas_livres > melhor["vagas_livres"]:
            melhor = {
                "id": medico["id"],
                "nome": medico["nome"],
                "especialidade": medico["especialidade"],
                "vagas_livres": vagas_livres,
            }
    cursor.close()
    return jsonify({"medico": melhor})


@rotas_paciente.route("/api/calculos-risco", methods=["POST"])
@paciente_obrigatorio
def api_salvar_calculo_risco():
    """Calcula, salva e retorna o risco cardiovascular informado pelo paciente."""

    usuario = session["usuario"]
    dados = request.get_json() or {}
    try:
        resultado = calcular_risco_framingham(
            sexo=dados.get("sexo"),
            idade=int(dados.get("idade")),
            colesterol_total=float(dados.get("colesterol_total")),
            hdl=float(dados.get("hdl")),
            pressao_sistolica=float(dados.get("pressao_sistolica")),
            trata_pressao=bool(dados.get("trata_pressao")),
            fumante=bool(dados.get("fumante")),
            diabetes=bool(dados.get("diabetes")),
        )
    except (TypeError, ValueError) as erro:
        return jsonify({"erro": str(erro)}), 400

    db = obter_banco()
    cursor = db.cursor()
    paciente_id = obter_paciente_id(usuario["id"])
    cursor.execute(
        """
        INSERT INTO calculos_risco
            (paciente_id, sexo, idade, colesterol_total, hdl, pressao_sistolica, trata_pressao, fumante, diabetes,
             risco_percentual, classe_risco, recomendacoes_json)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            paciente_id,
            dados.get("sexo"),
            dados.get("idade"),
            dados.get("colesterol_total"),
            dados.get("hdl"),
            dados.get("pressao_sistolica"),
            int(bool(dados.get("trata_pressao"))),
            int(bool(dados.get("fumante"))),
            int(bool(dados.get("diabetes"))),
            resultado["risco_percentual"],
            resultado["classe_risco"],
            json.dumps(resultado["recomendacoes"], ensure_ascii=False),
        ),
    )
    cursor.execute(
        """
        INSERT INTO prontuarios (paciente_id, medico_id, observacoes, alerta_risco)
        SELECT %s, d.id, %s, %s FROM medicos d ORDER BY d.id LIMIT 1
        """,
        (paciente_id, f"Cálculo Framingham: {resultado['risco_percentual']}% em 10 anos.", resultado["classe_risco"]),
    )
    db.commit()
    cursor.close()
    return jsonify(resultado)


@rotas_paciente.route("/api/metricas-saude")
@paciente_obrigatorio
def api_metricas_saude():
    """Entrega métricas de saúde do paciente em JSON para gráficos do painel."""

    usuario = session["usuario"]
    db = obter_banco()
    cursor = db.cursor()
    paciente_id = obter_paciente_id(usuario["id"])
    cursor.execute(
        """
        SELECT pressao_arterial, frequencia_cardiaca, peso, imc, glicemia, colesterol,
               DATE_FORMAT(medido_em, '%%Y-%%m-%%d') as data
        FROM metricas_saude
        WHERE paciente_id = %s
        ORDER BY medido_em ASC
        """,
        (paciente_id,),
    )
    metricas = cursor.fetchall()
    cursor.close()
    return jsonify(metricas)


@rotas_paciente.route("/notificacoes/<int:notif_id>/ler", methods=["POST"])
@paciente_obrigatorio
def marcar_notificacao_lida(notif_id):
    """Marca uma notificação específica como lida para o usuário logado."""

    usuario = session["usuario"]
    db = obter_banco()
    cursor = db.cursor()
    cursor.execute(
        "UPDATE notificacoes SET lida = 1, lida_em = NOW() WHERE id = %s AND usuario_id = %s",
        (notif_id, usuario["id"]),
    )
    db.commit()
    cursor.close()
    return jsonify({"sucesso": True})


@rotas_paciente.route("/notificacoes/ler-todas", methods=["POST"])
@paciente_obrigatorio
def marcar_todas_notificacoes_lidas():
    """Marca todas as notificações pendentes do paciente como lidas."""

    usuario = session["usuario"]
    db = obter_banco()
    cursor = db.cursor()
    cursor.execute(
        "UPDATE notificacoes SET lida = 1, lida_em = NOW() WHERE usuario_id = %s AND lida = 0",
        (usuario["id"],),
    )
    db.commit()
    cursor.close()
    return jsonify({"sucesso": True})


@rotas_paciente.route("/exames/<int:exame_id>/compartilhar", methods=["POST"])
@paciente_obrigatorio
def compartilhar_exame(exame_id):
    """Cria link temporário para compartilhar um exame pertencente ao paciente."""

    usuario = session["usuario"]
    db = obter_banco()
    cursor = db.cursor()
    paciente_id = obter_paciente_id(usuario["id"])
    exame = buscar_exame_paciente(cursor, exame_id, paciente_id)
    if not exame:
        cursor.close()
        return jsonify({"erro": "nao_encontrado"}), 404
    token = criar_token_compartilhamento(cursor, exame_id)
    db.commit()
    cursor.close()
    return jsonify({"url": url_for("publico.exame_compartilhado", token=token, _external=True), "horas_para_expirar": 48})


@rotas_paciente.route("/exames/<int:exame_id>/visualizar")
@paciente_obrigatorio
def visualizar_exame(exame_id):
    """Exibe o exame do paciente autenticado ou a simulação institucional segura."""

    usuario = session["usuario"]
    db = obter_banco()
    cursor = db.cursor()
    paciente_id = obter_paciente_id(usuario["id"])
    exame = buscar_exame_paciente(cursor, exame_id, paciente_id)
    cursor.close()
    if not exame:
        abort(404)

    caminho_origem = resolver_caminho_arquivo_exame(current_app.root_path, exame.get("arquivo_url"))
    arquivo_disponivel = bool(caminho_origem and caminho_origem.exists())
    visualizacao = montar_visualizacao_exame(exame, arquivo_disponivel=arquivo_disponivel)
    return render_template("visualizador_exame.html", exame=exame, visualizacao=visualizacao)


@rotas_paciente.route("/exames/<int:exame_id>/marca-dagua")
@paciente_obrigatorio
def baixar_exame_marca_dagua(exame_id):
    """Gera download de PDF com marca d'água contendo dados do paciente."""

    usuario = session["usuario"]
    db = obter_banco()
    cursor = db.cursor()
    paciente_id = obter_paciente_id(usuario["id"])
    exame = buscar_exame_paciente(cursor, exame_id, paciente_id)
    cursor.close()
    if not exame or exame.get("tipo_resultado") != "pdf" or not exame.get("arquivo_url"):
        abort(404)

    caminho_origem = resolver_caminho_arquivo_exame(current_app.root_path, exame["arquivo_url"])
    if not caminho_origem or not caminho_origem.exists():
        abort(404)

    try:
        saida_pdf = gerar_pdf_com_marca_dagua(
            caminho_origem,
            exame.get("nome_paciente") or "Paciente",
            exame.get("cpf_paciente") or "-",
        )
        return send_file(saida_pdf, mimetype="application/pdf", as_attachment=True, download_name=nome_download_exame(exame_id))
    except Exception:
        logger.exception("pdf_com_marca_dagua_falhou", extra={"extra": {"exame_id": exame_id}})
        abort(500)


@rotas_paciente.route("/teleconsulta/<int:consulta_id>")
@paciente_obrigatorio
def sala_espera_teleconsulta(consulta_id):
    """Abre a sala de espera virtual para consultas de telemedicina."""

    usuario = session["usuario"]
    db = obter_banco()
    cursor = db.cursor()
    paciente_id = obter_paciente_id(usuario["id"])
    cursor.execute(
        """
        SELECT a.*, s.nome as nome_servico, u.nome as nome_medico
        FROM consultas a
        JOIN servicos s ON a.servico_id = s.id
        JOIN medicos d ON a.medico_id = d.id
        JOIN usuarios u ON d.usuario_id = u.id
        WHERE a.id = %s AND a.paciente_id = %s
        """,
        (consulta_id, paciente_id),
    )
    consulta = cursor.fetchone()
    cursor.close()
    if not consulta or "teleconsulta" not in consulta["nome_servico"].lower():
        abort(404)
    consulta["url_sala"] = consulta.get("sala_teleconsulta_url") or f"https://meet.jit.si/cardiolab-{consulta_id}"
    return render_template("sala_espera_teleconsulta.html", consulta=consulta)


@rotas_paciente.route("/teleconsulta/<int:consulta_id>/fluxo-situacao")
@paciente_obrigatorio
def fluxo_situacao_teleconsulta(consulta_id):
    """Mantém fluxo SSE para informar ao paciente a situação da sala virtual."""

    usuario = session["usuario"]
    paciente_id = obter_paciente_id(usuario["id"])

    @stream_with_context
    def gerar():
        """Consulta periodicamente a situação da consulta e envia eventos ao navegador."""

        while True:
            db = obter_banco()
            cursor = db.cursor()
            cursor.execute(
                """
                SELECT situacao FROM consultas
                WHERE id = %s AND paciente_id = %s
                """,
                (consulta_id, paciente_id),
            )
            consulta = cursor.fetchone()
            cursor.close()
            situacao = "indisponivel"
            if consulta:
                situacao = "em atendimento" if consulta["situacao"] == "em_atendimento" else "disponivel"
            yield f"event: situacao-medico\ndata: {json.dumps({'situacao': situacao})}\n\n"
            time.sleep(10)

    return Response(gerar(), mimetype="text/event-stream", headers={"Cache-Control": "no-cache"})


@rotas_paciente.route("/exames")
@paciente_obrigatorio
def exames():
    """Redireciona o atalho de exames para a aba correspondente do painel."""

    return redirect(url_for("paciente.painel"))


@rotas_paciente.route("/saude")
@paciente_obrigatorio
def saude():
    """Redireciona o atalho de saúde para a aba correspondente do painel."""

    return redirect(url_for("paciente.painel"))


@rotas_paciente.route("/calculadora-risco")
@paciente_obrigatorio
def calculadora_risco():
    """Redireciona o atalho da calculadora para a aba de saúde do painel."""

    return redirect(url_for("paciente.painel"))






