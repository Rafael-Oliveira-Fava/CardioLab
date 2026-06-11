import re

from servicos.cpf import limpar_cpf, formatar_cpf


EXPRESSAO_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def normalizar_email(email):
    """Remove espaços e padroniza e-mail em letras minúsculas."""
    return (email or "").strip().lower()


def normalizar_nome(nome):
    """Remove espaços duplicados do nome informado no cadastro."""
    return " ".join((nome or "").strip().split())


def normalizar_cpf(cpf):
    """Limpa e formata CPF quando ele possui onze dígitos."""
    digitos = limpar_cpf(cpf)
    return formatar_cpf(digitos) if len(digitos) == 11 else (cpf or "").strip()


def email_valido(email):
    """Confere se o e-mail possui formato básico aceitável."""
    return bool(EXPRESSAO_EMAIL.match(normalizar_email(email)))


def encontrar_cpf_ou_email_repetido(banco, email, cpf, usuario_ignorado_id=None):
    """Busca usuário existente com o mesmo CPF ou e-mail."""
    email_normalizado = normalizar_email(email)
    cpf_formatado = normalizar_cpf(cpf)

    consulta = """
        SELECT id, email, cpf
        FROM usuarios
        WHERE (LOWER(email) = %s OR cpf = %s)
    """
    parametros = [email_normalizado, cpf_formatado]
    if usuario_ignorado_id:
        consulta += " AND id <> %s"
        parametros.append(usuario_ignorado_id)
    consulta += " LIMIT 1"

    cursor = banco.cursor()
    try:
        cursor.execute(consulta, tuple(parametros))
        return cursor.fetchone()
    finally:
        cursor.close()


def mensagem_cpf_ou_email_repetido(conflito, email, cpf):
    """Gera mensagem específica para CPF ou e-mail já cadastrado."""
    if not conflito:
        return None
    if normalizar_email(conflito.get("email")) == normalizar_email(email):
        return "E-mail já cadastrado no sistema."
    if normalizar_cpf(conflito.get("cpf")) == normalizar_cpf(cpf):
        return "CPF já cadastrado no sistema."
    return "CPF ou e-mail já cadastrado no sistema."


def mensagem_duplicidade_banco(erro):
    """Transforma erro de chave duplicada do banco em mensagem amigável."""
    mensagem = str(erro).lower()
    if "duplicate" not in mensagem and "duplic" not in mensagem:
        return None
    if "email" in mensagem:
        return "E-mail já cadastrado no sistema."
    if "cpf" in mensagem:
        return "CPF já cadastrado no sistema."
    return "CPF ou e-mail já cadastrado no sistema."

