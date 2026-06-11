from flask_mysqldb import MySQL
from apscheduler.schedulers.background import BackgroundScheduler


conexao_mysql = MySQL()
agendador = BackgroundScheduler(timezone="America/Sao_Paulo")


def obter_banco():
    """Entrega a conexão MySQL compartilhada no contexto atual do Flask."""

    return conexao_mysql.connection


def iniciar_extensoes(aplicacao):
    """Inicializa banco e agendador usados pelas rotas e tarefas."""

    conexao_mysql.init_app(aplicacao)
    aplicacao.obter_banco = obter_banco

    if aplicacao.config.get("AGENDADOR_ATIVO", True) and not aplicacao.config.get("TESTING"):
        from tarefas import registrar_lembretes_consulta

        if not agendador.running:
            agendador.add_job(
                registrar_lembretes_consulta,
                "interval",
                minutes=15,
                id="lembretes-consultas",
                replace_existing=True,
                args=[aplicacao],
            )
            agendador.start()

