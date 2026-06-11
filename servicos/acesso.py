from werkzeug.security import check_password_hash

from servicos.cpf import formatar_cpf, limpar_cpf
from servicos.usuarios import normalizar_email


def autenticar_usuario(banco, identificador, senha):
    """Confere e-mail/CPF e senha, retornando usuário ativo ou erro."""
    identificador = (identificador or "").strip()
    email_identificador = normalizar_email(identificador)
    cpf_digitos = limpar_cpf(identificador)
    cpf_identificador = formatar_cpf(cpf_digitos) if len(cpf_digitos) == 11 else identificador

    cursor = banco.cursor()
    cursor.execute(
        "SELECT * FROM usuarios WHERE LOWER(email) = %s OR cpf = %s",
        (email_identificador, cpf_identificador),
    )
    usuario = cursor.fetchone()
    cursor.close()

    if not usuario or not check_password_hash(usuario["senha_hash"], senha):
        return None, "credenciais_invalidas"
    if not usuario.get("ativo", 1):
        return None, "inativo"
    return usuario, None

