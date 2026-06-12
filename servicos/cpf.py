import re

def limpar_cpf(cpf):
    """Remove tudo que não é número de um CPF informado."""
    return re.sub(r"[^0-9]", "", cpf or "")

def formatar_cpf(cpf):
    """Aplica máscara brasileira quando o CPF possui onze dígitos."""
    digitos = limpar_cpf(cpf)
    if len(digitos) != 11:
        return cpf
    return f"{digitos[:3]}.{digitos[3:6]}.{digitos[6:9]}-{digitos[9:]}"

def validar_cpf(cpf):
    """Valida tamanho, repetição e dígitos verificadores de CPF."""
    digitos = limpar_cpf(cpf)
    if len(digitos) != 11:
        return False

    if digitos == digitos[0] * 11:
        return False

    primeira_soma = sum(int(digitos[indice]) * (10 - indice) for indice in range(9))
    primeiro_resto = primeira_soma % 11
    primeiro_digito = 0 if primeiro_resto < 2 else 11 - primeiro_resto
    if int(digitos[9]) != primeiro_digito:
        return False

    segunda_soma = sum(int(digitos[indice]) * (11 - indice) for indice in range(10))
    segundo_resto = segunda_soma % 11
    segundo_digito = 0 if segundo_resto < 2 else 11 - segundo_resto
    return int(digitos[10]) == segundo_digito
