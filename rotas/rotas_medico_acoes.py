"""
CardioLab - rotas de ações do médico.
Atualização de situação, fila de atendimento, envio de exames e foto de perfil.
"""

import logging
import os

from flask import current_app, flash, jsonify, redirect, request, session, url_for
from werkzeug.utils import secure_filename as nome_seguro_arquivo

from extensoes import obter_banco
from servicos.rotulos import rotulo_situacao_consulta
from servicos.fotos import salvar_foto_perfil
from rotas.rotas_medico import rotas_medico, medico_obrigatorio, obter_medico_id


logger = logging.getLogger(__name__)


@rotas_medico.route("/perfil/foto", methods=["POST"])
@medico_obrigatorio
def atualizar_foto_perfil():
    """Salva nova foto do médico e atualiza a sessão usada no cabeçalho."""

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
        logger.exception("atualizacao_foto_medico_falhou", extra={"extra": {"usuario_id": usuario["id"]}})
        flash("Não foi possível atualizar sua foto agora.", "perigo")
    return redirect(url_for("medico.painel"))


@rotas_medico.route("/consultas/<int:consulta_id>/situacao", methods=["POST"])
@medico_obrigatorio
def atualizar_situacao_consulta(consulta_id):
    """Atualiza a situação da consulta e cria notificações conforme a mudança."""

    usuario = session["usuario"]
    db = obter_banco()
    cursor = db.cursor()
    medico_id = obter_medico_id(usuario["id"])
    nova_situacao = request.form.get("situacao")
    situacoes_validas = ["agendada", "confirmada", "em_atendimento", "finalizada", "cancelada", "faltou"]
    if nova_situacao not in situacoes_validas:
        flash("Situação inválida.", "perigo")
        return redirect(url_for("medico.painel"))

    cursor.execute(
        """
        SELECT a.*, p.usuario_id as usuario_paciente_id, s.nome as nome_servico
        FROM consultas a
        JOIN pacientes p ON a.paciente_id = p.id
        JOIN servicos s ON a.servico_id = s.id
        WHERE a.id = %s AND a.medico_id = %s
        """,
        (consulta_id, medico_id),
    )
    consulta = cursor.fetchone()
    if not consulta:
        flash("Consulta não encontrada.", "perigo")
        cursor.close()
        return redirect(url_for("medico.painel"))

    motivo = request.form.get("motivo", "")
    url_sala = consulta.get("sala_teleconsulta_url")
    if nova_situacao == "confirmada" and "teleconsulta" in consulta["nome_servico"].lower():
        url_sala = f"https://meet.jit.si/cardiolab-{consulta_id}"

    cursor.execute(
        """
        UPDATE consultas
        SET situacao = %s,
            motivo_cancelamento = %s,
            sala_teleconsulta_url = COALESCE(%s, sala_teleconsulta_url),
            confirmada_em = CASE WHEN %s = 'confirmada' THEN NOW() ELSE confirmada_em END
        WHERE id = %s
        """,
        (nova_situacao, motivo if nova_situacao == "cancelada" else None, url_sala, nova_situacao, consulta_id),
    )

    if nova_situacao == "cancelada":
        cursor.execute(
            """
            INSERT INTO notificacoes (usuario_id, titulo, mensagem, tipo)
            VALUES (%s, 'Consulta Cancelada', %s, 'perigo')
            """,
            (
                consulta["usuario_paciente_id"],
                f"Sua consulta do dia {consulta['data_consulta']} foi cancelada. Motivo: {motivo}",
            ),
        )
    if nova_situacao == "finalizada":
        cursor.execute(
            """
            INSERT INTO notificacoes (usuario_id, titulo, mensagem, tipo)
            VALUES (%s, 'Avalie seu Atendimento',
                    'De 0 a 10, quanto você indicaria a CardioLab? Acesse o portal para avaliar.', 'informacao')
            """,
            (consulta["usuario_paciente_id"],),
        )

    db.commit()
    cursor.close()
    flash(f"Situação atualizada para: {rotulo_situacao_consulta(nova_situacao).lower()}", "sucesso")
    return redirect(url_for("medico.painel"))


@rotas_medico.route("/fila/reordenar", methods=["POST"])
@medico_obrigatorio
def reordenar_fila():
    """Persiste a sequência da fila de atendimento definida pelo médico."""

    usuario = session["usuario"]
    medico_id = obter_medico_id(usuario["id"])
    ids_consultas = (request.get_json() or {}).get("ids_consultas", [])
    db = obter_banco()
    cursor = db.cursor()
    for posicao, consulta_id in enumerate(ids_consultas, start=1):
        cursor.execute(
            "UPDATE consultas SET posicao_fila = %s WHERE id = %s AND medico_id = %s",
            (posicao, consulta_id, medico_id),
        )
    db.commit()
    cursor.close()
    return jsonify({"sucesso": True})


@rotas_medico.route("/exames/enviar", methods=["POST"])
@medico_obrigatorio
def enviar_exame():
    """Recebe laudo enviado pelo médico, salva arquivo e notifica o paciente."""

    usuario = session["usuario"]
    medico_id = obter_medico_id(usuario["id"])
    paciente_id = request.form.get("paciente_id")
    servico_id = request.form.get("servico_id") or None
    titulo = request.form.get("titulo", "Laudo cardiológico").strip()
    arquivo = request.files.get("arquivo")
    if not arquivo or not paciente_id:
        flash("Informe paciente e arquivo.", "perigo")
        return redirect(url_for("medico.painel"))

    nome_arquivo = nome_seguro_arquivo(arquivo.filename)
    pasta_envio = os.path.join(current_app.config["PASTA_ARQUIVOS"], "exames")
    os.makedirs(pasta_envio, exist_ok=True)
    caminho_arquivo = os.path.join(pasta_envio, nome_arquivo)
    arquivo.save(caminho_arquivo)
    arquivo_url = url_for("static", filename=f"arquivos_enviados/exames/{nome_arquivo}")
    tipo_resultado = "pdf" if nome_arquivo.lower().endswith(".pdf") else "imagem"

    db = obter_banco()
    cursor = db.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO resultados_exames
                (paciente_id, medico_id, servico_id, titulo, arquivo_url, tipo_resultado, assinatura_digital)
            VALUES (%s, %s, %s, %s, %s, %s,
                    (SELECT CONCAT(u.nome, ' - ', d.crm) FROM medicos d JOIN usuarios u ON d.usuario_id = u.id WHERE d.id = %s))
            """,
            (paciente_id, medico_id, servico_id, titulo, arquivo_url, tipo_resultado, medico_id),
        )
        cursor.execute(
            """
            INSERT INTO notificacoes (usuario_id, titulo, mensagem, tipo)
            SELECT p.usuario_id, 'Exame disponível', %s, 'sucesso' FROM pacientes p WHERE p.id = %s
            """,
            (f"O resultado {titulo} está disponível no portal.", paciente_id),
        )
        db.commit()
        flash("Laudo enviado com sucesso.", "sucesso")
    except Exception:
        db.rollback()
        logger.exception("envio_exame_falhou", extra={"extra": {"paciente_id": paciente_id}})
        flash("Erro ao enviar laudo.", "perigo")
    finally:
        cursor.close()
    return redirect(url_for("medico.painel"))


@rotas_medico.route("/exames")
@medico_obrigatorio
def exames():
    """Redireciona o atalho de exames para o painel médico."""

    return redirect(url_for("medico.painel"))
