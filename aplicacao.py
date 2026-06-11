"""
CardioLab - Plataforma de Cardiologia
Aplicação Flask principal.
"""

import os

from flask import Flask, request, session

from configuracao_logs import configurar_logs
from configuracao import Configuracao
from extensoes import iniciar_extensoes, obter_banco
from servicos.formatacao import (
    dia_semana_curto,
    dia_do_mes,
    formatar_data_br,
    formatar_data_curta,
    formatar_data_hora_curta,
    formatar_horario,
    mes_abreviado,
)
from servicos.rotulos import (
    rotulo_classe_risco,
    rotulo_perfil_usuario,
    rotulo_situacao_carteirinha,
    rotulo_situacao_consulta,
)


def criar_aplicacao():
    """Cria e configura a aplicação Flask."""
    aplicacao = Flask(__name__)
    aplicacao.config.from_object(Configuracao)

    os.makedirs(aplicacao.config.get("PASTA_ARQUIVOS", "static/arquivos_enviados"), exist_ok=True)

    configurar_logs(aplicacao)
    iniciar_extensoes(aplicacao)
    registrar_filtros_template(aplicacao)

    def versao_estatica():
        """Calcula a versão dos arquivos estáticos pela data da última alteração.

        O valor é usado nos links de CSS e JavaScript para invalidar o cache do
        navegador sempre que um arquivo relevante do front-end é atualizado.
        """
        try:
            pastas_css = [
                os.path.join(aplicacao.static_folder, "css", "autenticacao"),
                os.path.join(aplicacao.static_folder, "css", "painel"),
                os.path.join(aplicacao.static_folder, "css", "site"),
            ]
            caminhos_observados = [
                os.path.join(aplicacao.static_folder, "css", "site.css"),
                os.path.join(aplicacao.static_folder, "css", "autenticacao.css"),
                os.path.join(aplicacao.static_folder, "css", "painel.css"),
                os.path.join(aplicacao.static_folder, "js", "portal_publico.js"),
                os.path.join(aplicacao.static_folder, "js", "autenticacao.js"),
                os.path.join(aplicacao.static_folder, "js", "abas_painel.js"),
                os.path.join(aplicacao.static_folder, "js", "consultas_paciente.js"),
                os.path.join(aplicacao.static_folder, "js", "calculadora_risco.js"),
                os.path.join(aplicacao.static_folder, "js", "medico_prontuarios.js"),
            ]
            for pasta_css in pastas_css:
                if os.path.isdir(pasta_css):
                    caminhos_observados.extend(
                        os.path.join(pasta_css, nome_arquivo)
                        for nome_arquivo in os.listdir(pasta_css)
                        if nome_arquivo.endswith(".css")
                    )
            return str(int(max(os.path.getmtime(caminho) for caminho in caminhos_observados)))
        except OSError:
            return "1"

    @aplicacao.context_processor
    def injetar_globais():
        """Disponibiliza dados globais que todos os templates podem usar."""
        usuario = session.get("usuario", None)
        return {
            "numero_whatsapp": Configuracao.NUMERO_WHATSAPP,
            "mensagem_whatsapp": Configuracao.MENSAGEM_WHATSAPP,
            "telefone_clinica_formatado": "(11) 99999-9999",
            "email_clinica": "atendimento@cardiolab.com.br",
            "email_lgpd": "lgpd@cardiolab.com.br",
            "usuario_atual": usuario,
            "total_notificacoes_nao_lidas": contar_notificacoes_nao_lidas(usuario),
            "versao_estatica": versao_estatica(),
        }

    def contar_notificacoes_nao_lidas(usuario):
        """Conta notificações não lidas do usuário logado para exibir no menu."""
        if not usuario:
            return 0
        try:
            banco = obter_banco()
            cursor = banco.cursor()
            cursor.execute(
                "SELECT COUNT(*) as total FROM notificacoes WHERE usuario_id = %s AND lida = 0",
                (usuario["id"],),
            )
            linha = cursor.fetchone()
            cursor.close()
            return linha["total"] if linha else 0
        except Exception:
            aplicacao.logger.exception("contagem_notificacoes_falhou", extra={"extra": {"usuario_id": usuario.get("id")}})
            return 0

    @aplicacao.after_request
    def aplicar_cabecalhos_resposta(resposta):
        """Aplica cabeçalhos de segurança e política de cache em cada resposta."""
        resposta.headers.setdefault("X-Content-Type-Options", "nosniff")
        resposta.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        resposta.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        if request.path.startswith("/static/"):
            ambiente_desenvolvimento = aplicacao.debug or aplicacao.config.get("AMBIENTE_APLICACAO") == "desenvolvimento"
            if ambiente_desenvolvimento:
                resposta.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
                resposta.headers["Pragma"] = "no-cache"
                resposta.headers["Expires"] = "0"
            else:
                resposta.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        return resposta

    from rotas.rotas_administracao import rotas_administracao
    from rotas.rotas_api import rotas_api
    from rotas.rotas_autenticacao import rotas_autenticacao
    from rotas.rotas_medico import rotas_medico
    from rotas.rotas_paciente import rotas_paciente
    from rotas.rotas_publicas import rotas_publicas

    aplicacao.register_blueprint(rotas_publicas)
    aplicacao.register_blueprint(rotas_autenticacao)
    aplicacao.register_blueprint(rotas_paciente)
    aplicacao.register_blueprint(rotas_medico)
    aplicacao.register_blueprint(rotas_administracao)
    aplicacao.register_blueprint(rotas_api)

    @aplicacao.errorhandler(404)
    def pagina_nao_encontrada(_erro):
        """Renderiza a tela padronizada quando uma URL não existe."""
        return renderizar_erro("Página não encontrada", "A página que você está procurando não existe.", 404), 404

    @aplicacao.errorhandler(500)
    def erro_interno(_erro):
        """Renderiza a tela padronizada quando ocorre erro interno."""
        return renderizar_erro("Erro Interno", "Ocorreu um erro inesperado. Tente novamente mais tarde.", 500), 500

    def renderizar_erro(titulo, mensagem, codigo):
        """Monta a página de erro usando título, mensagem e código HTTP."""
        from flask import render_template

        return render_template("erro.html", titulo_erro=titulo, mensagem_erro=mensagem, codigo_erro=codigo)

    return aplicacao


def registrar_filtros_template(aplicacao):
    """Registra filtros de apresentação usados pelos templates."""
    aplicacao.jinja_env.filters["rotulo_perfil"] = rotulo_perfil_usuario
    aplicacao.jinja_env.filters["rotulo_carteirinha"] = rotulo_situacao_carteirinha
    aplicacao.jinja_env.filters["classe_situacao_carteirinha"] = classe_situacao_carteirinha
    aplicacao.jinja_env.filters["rotulo_consulta"] = rotulo_situacao_consulta
    aplicacao.jinja_env.filters["rotulo_risco"] = rotulo_classe_risco
    aplicacao.jinja_env.filters["data_br"] = formatar_data_br
    aplicacao.jinja_env.filters["data_curta"] = formatar_data_curta
    aplicacao.jinja_env.filters["data_hora_curta"] = formatar_data_hora_curta
    aplicacao.jinja_env.filters["horario"] = formatar_horario
    aplicacao.jinja_env.filters["mes_abreviado"] = mes_abreviado
    aplicacao.jinja_env.filters["dia_mes"] = dia_do_mes
    aplicacao.jinja_env.filters["dia_semana"] = dia_semana_curto


def classe_situacao_carteirinha(valor):
    """Converte a situação interna da carteirinha em classe CSS em português."""
    classes_css = {
        "ativa": "ativo",
        "em_analise": "pendente",
        "expirada": "expirado",
        "cancelada": "cancelado",
    }
    return classes_css.get(valor, "pendente")


aplicacao = criar_aplicacao()


if __name__ == "__main__":
    aplicacao.run(debug=True, host="0.0.0.0", port=5000)



