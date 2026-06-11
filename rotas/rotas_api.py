"""APIs JSON e eventos em tempo real compartilhados pelo sistema."""

import json
import time

from flask import Blueprint, Response, jsonify, request, session, stream_with_context

from extensoes import obter_banco
from servicos.risco import calcular_risco_framingham


rotas_api = Blueprint("api", __name__, url_prefix="/api")


@rotas_api.route("/risco/framingham", methods=["POST"])
def previa_framingham():
    """Calcula uma prévia do risco de Framingham sem salvar no prontuário."""
    dados = request.get_json() or request.form
    try:
        resultado = calcular_risco_framingham(
            sexo=dados.get("sexo"),
            idade=int(dados.get("idade")),
            colesterol_total=float(dados.get("colesterol_total")),
            hdl=float(dados.get("hdl")),
            pressao_sistolica=float(dados.get("pressao_sistolica")),
            trata_pressao=valor_verdadeiro(dados.get("trata_pressao")),
            fumante=valor_verdadeiro(dados.get("fumante")),
            diabetes=valor_verdadeiro(dados.get("diabetes")),
        )
    except (TypeError, ValueError) as erro:
        return jsonify({"erro": str(erro)}), 400
    return jsonify(resultado)


def valor_verdadeiro(valor):
    """Interpreta valores de formulário e JSON como verdadeiro."""
    return valor is True or str(valor).lower() in ("1", "verdadeiro", "sim")


@rotas_api.route("/fluxo")
def fluxo_notificacoes():
    """Mantém um canal SSE aberto para atualizar notificações no menu."""
    if "usuario" not in session:
        return Response("event: erro\ndata: nao_autorizado\n\n", mimetype="text/event-stream", status=401)

    usuario_id = session["usuario"]["id"]

    @stream_with_context
    def gerar():
        """Envia periodicamente o total e as últimas notificações não lidas."""
        while True:
            db = obter_banco()
            cursor = db.cursor()
            cursor.execute(
                """
                SELECT id, titulo, mensagem, tipo, criado_em
                FROM notificacoes
                WHERE usuario_id = %s AND lida = 0
                ORDER BY criado_em DESC
                LIMIT 5
                """,
                (usuario_id,),
            )
            notificacoes = cursor.fetchall()
            cursor.execute(
                "SELECT COUNT(*) as total FROM notificacoes WHERE usuario_id = %s AND lida = 0",
                (usuario_id,),
            )
            total_nao_lidas = cursor.fetchone()["total"]
            cursor.close()
            dados = {
                "nao_lidas": total_nao_lidas,
                "atualizado_em": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "notificacoes": [
                    {
                        "id": item["id"],
                        "titulo": item["titulo"],
                        "mensagem": item["mensagem"],
                        "tipo": item["tipo"],
                        "criado_em": str(item["criado_em"]),
                    }
                    for item in notificacoes
                ],
            }
            yield f"event: notificacoes\ndata: {json.dumps(dados, ensure_ascii=False)}\n\n"
            time.sleep(20)

    cabecalhos = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    return Response(gerar(), mimetype="text/event-stream", headers=cabecalhos)


