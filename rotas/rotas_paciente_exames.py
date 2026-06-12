"""
CardioLab - rotas de exames do paciente.
Compartilhamento, visualização e download com marca d'água.
"""

import logging

from flask import abort, current_app, flash, jsonify, redirect, render_template, request, send_file, session, url_for

from extensoes import obter_banco
from servicos.exames import (
    buscar_exame_paciente,
    criar_token_compartilhamento,
    gerar_pdf_com_marca_dagua,
    montar_visualizacao_exame,
    nome_download_exame,
    resolver_caminho_arquivo_exame,
)
from rotas.rotas_paciente import rotas_paciente, paciente_obrigatorio, obter_paciente_id


logger = logging.getLogger(__name__)


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


@rotas_paciente.route("/exames")
@paciente_obrigatorio
def exames():
    """Redireciona o atalho de exames para a aba correspondente do painel."""

    return redirect(url_for("paciente.painel"))
