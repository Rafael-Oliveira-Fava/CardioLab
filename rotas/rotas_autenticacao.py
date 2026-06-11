"""Rotas de autenticação, cadastro e solicitação administrativa de senha."""

import logging

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from werkzeug.security import generate_password_hash

from extensoes import obter_banco
from servicos.acesso import autenticar_usuario
from servicos.cpf import formatar_cpf, limpar_cpf, validar_cpf
from servicos.solicitacoes_senha import criar_solicitacao_redefinicao_senha
from servicos.usuarios import (
    email_valido,
    encontrar_cpf_ou_email_repetido,
    mensagem_cpf_ou_email_repetido,
    mensagem_duplicidade_banco,
    normalizar_email,
    normalizar_nome,
)


rotas_autenticacao = Blueprint("autenticacao", __name__)
logger = logging.getLogger(__name__)


def redirecionamento_seguro(proximo_endereco):
    """Garante que o redirecionamento pós-login aponte para uma rota interna."""
    return bool(proximo_endereco) and proximo_endereco.startswith("/") and not proximo_endereco.startswith("//")


def registrar_auditoria(usuario_id, acao, endereco_ip):
    """Registra ações sensíveis sem derrubar a aplicação se o log falhar."""
    try:
        db = obter_banco()
        cursor = db.cursor()
        cursor.execute(
            "INSERT INTO auditoria (usuario_id, acao, endereco_ip) VALUES (%s, %s, %s)",
            (usuario_id, acao, endereco_ip),
        )
        db.commit()
        cursor.close()
    except Exception:
        logger.exception(
            "registro_auditoria_falhou",
            extra={"extra": {"usuario_id": usuario_id, "acao": acao, "endereco_ip": endereco_ip}},
        )


@rotas_autenticacao.route("/login", methods=["GET", "POST"])
@rotas_autenticacao.route("/entrar", methods=["GET", "POST"])
def entrar():
    """Autentica usuário por e-mail ou CPF e redireciona conforme o perfil."""
    proximo_endereco = request.args.get("proximo") or request.form.get("proximo")
    if request.method == "POST":
        identificador = request.form.get("identificador", "").strip()
        senha = request.form.get("senha", "")

        if not identificador or not senha:
            flash("Preencha todos os campos.", "perigo")
            return render_template("entrada.html", proximo_endereco=proximo_endereco if redirecionamento_seguro(proximo_endereco) else None)

        db = obter_banco()
        usuario, erro = autenticar_usuario(db, identificador, senha)

        if usuario:
            session["usuario"] = {
                "id": usuario["id"],
                "nome": usuario["nome"],
                "email": usuario["email"],
                "perfil": usuario["perfil"],
                "foto_perfil": usuario.get("foto_perfil"),
            }
            session.permanent = True
            registrar_auditoria(usuario["id"], "ENTRADA", request.remote_addr)

            if redirecionamento_seguro(proximo_endereco):
                return redirect(proximo_endereco)
            if usuario["perfil"] == "medico":
                return redirect(url_for("medico.painel"))
            if usuario["perfil"] == "administrador":
                return redirect(url_for("administracao.painel"))
            return redirect(url_for("paciente.painel"))

        if erro == "inativo":
            flash("Conta desativada. Entre em contato com a administração.", "perigo")
        else:
            flash("E-mail/CPF ou senha inválidos.", "perigo")
            registrar_auditoria(None, f"ENTRADA_FALHOU: {identificador}", request.remote_addr)

    return render_template("entrada.html", proximo_endereco=proximo_endereco if redirecionamento_seguro(proximo_endereco) else None)


@rotas_autenticacao.route("/cadastro", methods=["GET", "POST"])
def cadastro():
    """Cria conta de paciente com CPF, e-mail e aceite de termos validados."""
    if request.method == "POST":
        nome = normalizar_nome(request.form.get("nome", ""))
        cpf = request.form.get("cpf", "").strip()
        email = normalizar_email(request.form.get("email", ""))
        telefone = request.form.get("telefone", "").strip()
        data_nascimento = request.form.get("data_nascimento", "").strip()
        cep = request.form.get("cep", "").strip()
        endereco = request.form.get("endereco", "").strip()
        senha = request.form.get("senha", "")
        confirmar_senha = request.form.get("confirmar_senha", "")
        aceite = request.form.get("aceite")

        erros = []
        if not all([nome, cpf, email, senha, confirmar_senha]):
            erros.append("Preencha todos os campos obrigatórios.")
        if senha != confirmar_senha:
            erros.append("As senhas não conferem.")
        if len(senha) < 6:
            erros.append("A senha deve ter pelo menos 6 caracteres.")
        if not email_valido(email):
            erros.append("E-mail inválido.")

        cpf_limpo = limpar_cpf(cpf)
        if not validar_cpf(cpf_limpo):
            erros.append("CPF inválido.")
        if not aceite:
            erros.append("Você precisa aceitar os termos de uso e política de privacidade.")

        if erros:
            for erro in erros:
                flash(erro, "perigo")
            return render_template("entrada.html", aba_autenticacao="cadastro")

        cpf_formatado = formatar_cpf(cpf_limpo)
        db = obter_banco()
        conflito = encontrar_cpf_ou_email_repetido(db, email, cpf_formatado)
        if conflito:
            flash(mensagem_cpf_ou_email_repetido(conflito, email, cpf_formatado), "perigo")
            return render_template("entrada.html", aba_autenticacao="cadastro")

        cursor = db.cursor()
        try:
            senha_hash = generate_password_hash(senha, method="pbkdf2:sha256")
            cursor.execute(
                "INSERT INTO usuarios (nome, email, cpf, senha_hash, perfil) VALUES (%s, %s, %s, %s, 'paciente')",
                (nome, email, cpf_formatado, senha_hash),
            )
            usuario_id = cursor.lastrowid
            cursor.execute(
                "INSERT INTO pacientes (usuario_id, data_nascimento, telefone, cep, endereco) VALUES (%s, %s, %s, %s, %s)",
                (usuario_id, data_nascimento or None, telefone, cep, endereco),
            )
            cursor.execute(
                "INSERT INTO consentimentos (usuario_id, tipo_consentimento, aceito) VALUES (%s, 'termos_e_privacidade', 1)",
                (usuario_id,),
            )
            db.commit()
            registrar_auditoria(usuario_id, "CADASTRO", request.remote_addr)
            flash("Cadastro realizado com sucesso! Faça login para acessar.", "sucesso")
            return redirect(url_for("autenticacao.entrar"))
        except Exception as erro:
            db.rollback()
            logger.exception("cadastro_falhou", extra={"extra": {"email": email}})
            flash(mensagem_duplicidade_banco(erro) or "Erro ao realizar cadastro. Tente novamente.", "perigo")
        finally:
            cursor.close()

    return render_template("entrada.html", aba_autenticacao="cadastro")


@rotas_autenticacao.route("/sair")
def sair():
    """Registra saída, limpa a sessão e devolve o usuário para a área pública."""
    usuario = session.get("usuario")
    if usuario:
        registrar_auditoria(usuario["id"], "SAIDA", request.remote_addr)
    session.clear()
    flash("Você saiu da sua conta com sucesso.", "sucesso")
    return redirect(url_for("publico.inicio"))


@rotas_autenticacao.route("/recuperar-senha", methods=["GET", "POST"])
def solicitar_redefinicao_senha():
    """Abre uma solicitação para que um administrador redefina a senha."""
    if request.method == "POST":
        identificador = request.form.get("identificador", "").strip()
        if not identificador:
            flash("Informe seu e-mail ou CPF.", "perigo")
            return render_template("recuperar_senha.html")

        db = obter_banco()
        try:
            usuario, criada = criar_solicitacao_redefinicao_senha(db, identificador, request.remote_addr)
            if usuario and criada:
                registrar_auditoria(usuario["id"], "SOLICITACAO_SENHA_ABERTA", request.remote_addr)
            elif usuario:
                registrar_auditoria(usuario["id"], "SOLICITACAO_SENHA_JA_EXISTE", request.remote_addr)
            else:
                registrar_auditoria(None, f"SOLICITACAO_SENHA_NAO_LOCALIZADA: {identificador}", request.remote_addr)
        except Exception:
            logger.exception("solicitacao_redefinicao_senha_falhou")
            flash("Não foi possível registrar a solicitação agora. Tente novamente.", "perigo")
            return render_template("recuperar_senha.html")

        flash("Se o cadastro estiver ativo, a administração receberá sua solicitação para redefinir a senha.", "informacao")

    return render_template("recuperar_senha.html")



