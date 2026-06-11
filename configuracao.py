import os

from dotenv import load_dotenv


load_dotenv()

class Configuracao:
    """Centraliza variáveis de ambiente e padrões técnicos da aplicação."""

    SECRET_KEY = os.environ.get('SECRET_KEY', 'cardiolab-secret-key-2024-mudar-em-producao')
    AMBIENTE_APLICACAO = os.environ.get('AMBIENTE_APLICACAO', 'desenvolvimento')
    NIVEL_LOG = os.environ.get('NIVEL_LOG')

    MYSQL_HOST = os.environ.get('MYSQL_HOST', 'localhost')
    MYSQL_USER = os.environ.get('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', '')
    MYSQL_DB = os.environ.get('MYSQL_DB', 'cardiolab')
    MYSQL_CURSORCLASS = 'DictCursor'

    SESSION_TYPE = 'filesystem'
    PERMANENT_SESSION_LIFETIME = 3600

    PASTA_ARQUIVOS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'arquivos_enviados')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024

    AGENDADOR_ATIVO = os.environ.get('AGENDADOR_ATIVO', 'true').lower() == 'true'

    NUMERO_WHATSAPP = '5511999999999'
    MENSAGEM_WHATSAPP = 'Olá! Gostaria de agendar uma consulta na CardioLab.'

    HORAS_MINIMAS_CANCELAMENTO = 12
    MINUTOS_INTERVALO_CONSULTA = 30

