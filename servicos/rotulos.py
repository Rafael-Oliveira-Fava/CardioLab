"""Rótulos de apresentação para valores técnicos do sistema."""


ROTULOS_PERFIL_USUARIO = {
    "paciente": "Paciente",
    "medico": "Médico",
    "administrador": "Administração",
}

ROTULOS_SITUACAO_CARTEIRINHA = {
    "em_analise": "Em análise",
    "ativa": "Ativa",
    "expirada": "Expirada",
    "cancelada": "Cancelada",
}

ROTULOS_SITUACAO_CONSULTA = {
    "agendada": "Agendada",
    "confirmada": "Confirmada",
    "em_atendimento": "Em atendimento",
    "finalizada": "Finalizada",
    "cancelada": "Cancelada",
    "faltou": "Faltou",
}

ROTULOS_RISCO = {
    "baixo": "Baixo",
    "intermediario": "Intermediário",
    "moderado": "Moderado",
    "alto": "Alto",
}


def rotulo_perfil_usuario(valor):
    """Traduz o perfil técnico do banco para texto visível no painel."""
    return ROTULOS_PERFIL_USUARIO.get(valor, str(valor or "").replace("_", " ").title())


def rotulo_situacao_carteirinha(valor):
    """Traduz a situação técnica da carteirinha para texto do usuário."""
    return ROTULOS_SITUACAO_CARTEIRINHA.get(valor, str(valor or "").replace("_", " ").title())


def rotulo_situacao_consulta(valor):
    """Traduz a situação técnica da consulta para texto do usuário."""
    return ROTULOS_SITUACAO_CONSULTA.get(valor, str(valor or "").replace("_", " ").title())


def rotulo_classe_risco(valor):
    """Traduz a classe técnica de risco cardiovascular para texto do usuário."""
    return ROTULOS_RISCO.get(valor, str(valor or "").replace("_", " ").title())

