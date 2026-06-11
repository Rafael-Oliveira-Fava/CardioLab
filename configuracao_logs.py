import json
import logging
import sys
from datetime import datetime, timezone

from flask import has_request_context, request, session


class FormatadorJson(logging.Formatter):
    """Formata logs em JSON para facilitar busca e diagnóstico em produção."""

    def format(self, registro):
        """Transforma um registro de log em texto JSON com contexto da requisição."""

        dados_log = {
            "momento": datetime.now(timezone.utc).isoformat(),
            "nivel": registro.levelname,
            "registrador": registro.name,
            "mensagem": registro.getMessage(),
            "modulo": registro.module,
            "funcao": registro.funcName,
            "linha": registro.lineno,
        }

        if has_request_context():
            dados_log.update(
                {
                    "metodo": request.method,
                    "caminho": request.path,
                    "endereco_remoto": request.headers.get("X-Forwarded-For", request.remote_addr),
                    "usuario_id": (session.get("usuario") or {}).get("id"),
                }
            )

        if registro.exc_info:
            dados_log["excecao"] = self.formatException(registro.exc_info)

        if hasattr(registro, "extra") and isinstance(registro.extra, dict):
            dados_log.update(registro.extra)

        return json.dumps(dados_log, ensure_ascii=False, default=str)


def configurar_logs(aplicacao):
    """Configura nível, saída e formato de logs da aplicação Flask."""

    ambiente = aplicacao.config.get("AMBIENTE_APLICACAO", "development").lower()
    nome_nivel = aplicacao.config.get("NIVEL_LOG") or ("DEBUG" if ambiente == "desenvolvimento" else "INFO")
    nivel = getattr(logging, str(nome_nivel).upper(), logging.INFO)

    manipulador = logging.StreamHandler(sys.stdout)
    manipulador.setFormatter(FormatadorJson())

    registrador_raiz = logging.getLogger()
    registrador_raiz.handlers.clear()
    registrador_raiz.addHandler(manipulador)
    registrador_raiz.setLevel(nivel)

    aplicacao.logger.handlers.clear()
    aplicacao.logger.propagate = True
    aplicacao.logger.setLevel(nivel)


