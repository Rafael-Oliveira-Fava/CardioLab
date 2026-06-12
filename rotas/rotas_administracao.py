"""
CardioLab - painel administrativo.
"""

import csv
import io
from functools import wraps

from flask import Blueprint, Response, flash, redirect, render_template, request, session, url_for
from werkzeug.security import generate_password_hash

from extensoes import obter_banco
from servicos.cpf import limpar_cpf, formatar_cpf, validar_cpf
from servicos.rotulos import rotulo_situacao_carteirinha
from servicos.carteirinha import garantir_schema_carteirinha
from servicos.solicitacoes_senha import (
    cancelar_solicitacao_redefinicao_senha,
    concluir_solicitacao_redefinicao_senha,
    garantir_tabela_solicitacoes_senha,
    listar_solicitacoes_redefinicao_senha,
)
from servicos.usuarios import (
    email_valido,
    encontrar_cpf_ou_email_repetido,
    mensagem_cpf_ou_email_repetido,
    mensagem_duplicidade_banco,
    normalizar_email,
    normalizar_nome,
)


rotas_administracao = Blueprint("administracao", __name__, url_prefix="/administracao")


def administrador_obrigatorio(f):
    """Protege rotas que só podem ser acessadas por administradores logados."""

    @wraps(f)
    def decorated(*args, **kwargs):
        """Confere sessão, perfil do usuário e libera a rota original."""

        if "usuario" not in session:
            flash("Faça login para acessar esta página.", "atencao")
            return redirect(url_for("autenticacao.entrar"))
        if session["usuario"]["perfil"] != "administrador":
            flash("Acesso restrito à administração.", "perigo")
            return redirect(url_for("publico.inicio"))
        return f(*args, **kwargs)

    return decorated


@rotas_administracao.route("/painel")
@administrador_obrigatorio
def painel():
    """Monta indicadores, usuários, auditoria e carteirinhas do painel administrativo."""

    db = obter_banco()
    garantir_schema_carteirinha(db)
    garantir_tabela_solicitacoes_senha(db)
    cursor = db.cursor()
    cursor.execute(
        """
        SELECT
            COUNT(CASE WHEN data_consulta = CURDATE() THEN 1 END) as consultas_hoje,
            ROUND(100 * COUNT(CASE WHEN situacao IN ('agendada', 'confirmada', 'em_atendimento') THEN 1 END)
                  / NULLIF(COUNT(*), 0), 1) as taxa_ocupacao,
            COUNT(CASE WHEN situacao = 'finalizada' THEN 1 END) * 280 as receita_estimada
        FROM consultas
        WHERE data_consulta >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
        """
    )
    indicadores = cursor.fetchone()
    cursor.execute("SELECT ROUND(AVG(nota), 1) as media_nps FROM avaliacoes WHERE tipo = 'nps'")
    indicadores["media_nps"] = (cursor.fetchone() or {}).get("media_nps") or 0

    cursor.execute("SELECT id, nome, email, cpf, perfil, ativo, criado_em FROM usuarios ORDER BY criado_em DESC LIMIT 50")
    usuarios = cursor.fetchall()
    cursor.execute(
        """
        SELECT al.*, u.nome as nome_usuario
        FROM auditoria al
        LEFT JOIN usuarios u ON al.usuario_id = u.id
        ORDER BY al.criado_em DESC
        LIMIT 80
        """
    )
    auditorias = cursor.fetchall()
    cursor.execute("SELECT chave, valor FROM configuracoes_clinica")
    configuracoes = {linha["chave"]: linha["valor"] for linha in cursor.fetchall()}
    cursor.execute(
        """
        SELECT pm.*, mp.nome as nome_plano, u.nome as nome_paciente, u.email, p.telefone
        FROM carteirinhas_pacientes pm
        JOIN planos_carteirinha mp ON pm.plano_id = mp.id
        JOIN pacientes p ON pm.paciente_id = p.id
        JOIN usuarios u ON p.usuario_id = u.id
        ORDER BY FIELD(pm.situacao, 'em_analise', 'ativa', 'expirada', 'cancelada'), pm.criado_em DESC
        LIMIT 40
        """
    )
    carteirinhas = cursor.fetchall()
    solicitacoes_senha = listar_solicitacoes_redefinicao_senha(cursor)
    cursor.close()
    return render_template(
        "painel_administracao.html",
        indicadores=indicadores,
        usuarios=usuarios,
        auditorias=auditorias,
        configuracoes=configuracoes,
        carteirinhas=carteirinhas,
        solicitacoes_senha=solicitacoes_senha,
    )


@rotas_administracao.route("/usuarios", methods=["POST"])
@administrador_obrigatorio
def criar_usuario():
    """Valida dados administrativos e cria paciente, médico ou administrador."""

    nome = normalizar_nome(request.form.get("nome", ""))
    email = normalizar_email(request.form.get("email", ""))
    cpf = request.form.get("cpf", "").strip()
    perfil = request.form.get("perfil", "paciente")
    senha = request.form.get("senha", "cardiolab123")
    cpf_limpo = limpar_cpf(cpf)
    if perfil not in ("paciente", "medico", "administrador") or not nome or not email_valido(email) or not validar_cpf(cpf_limpo):
        flash("Dados inválidos para criar usuário.", "perigo")
        return redirect(url_for("administracao.painel"))

    cpf_formatado = formatar_cpf(cpf_limpo)
    db = obter_banco()
    conflito = encontrar_cpf_ou_email_repetido(db, email, cpf_formatado)
    if conflito:
        flash(mensagem_cpf_ou_email_repetido(conflito, email, cpf_formatado), "perigo")
        return redirect(url_for("administracao.painel"))

    cursor = db.cursor()
    try:
        if perfil == "medico":
            crm = request.form.get("crm", "CRM pendente").strip()
            cursor.execute("SELECT id FROM medicos WHERE crm = %s LIMIT 1", (crm,))
            if cursor.fetchone():
                flash("CRM já cadastrado para outro médico.", "perigo")
                return redirect(url_for("administracao.painel"))

        cursor.execute(
            "INSERT INTO usuarios (nome, email, cpf, senha_hash, perfil) VALUES (%s, %s, %s, %s, %s)",
            (nome, email, cpf_formatado, generate_password_hash(senha, method="pbkdf2:sha256"), perfil),
        )
        usuario_id = cursor.lastrowid
        if perfil == "paciente":
            cursor.execute("INSERT INTO pacientes (usuario_id) VALUES (%s)", (usuario_id,))
        if perfil == "medico":
            cursor.execute(
                "INSERT INTO medicos (usuario_id, especialidade, crm) VALUES (%s, %s, %s)",
                (usuario_id, request.form.get("especialidade", "Cardiologia"), request.form.get("crm", "CRM pendente").strip()),
            )
        db.commit()
        flash("Usuário criado.", "sucesso")
    except Exception as erro:
        db.rollback()
        flash(mensagem_duplicidade_banco(erro) or "Não foi possível criar o usuário.", "perigo")
    finally:
        cursor.close()
    return redirect(url_for("administracao.painel"))


@rotas_administracao.route("/usuarios/<int:usuario_id>/alternar", methods=["POST"])
@administrador_obrigatorio
def alternar_usuario(usuario_id):
    """Alterna a situação ativo/inativo de uma conta do sistema."""

    db = obter_banco()
    cursor = db.cursor()
    cursor.execute("UPDATE usuarios SET ativo = IF(ativo = 1, 0, 1) WHERE id = %s", (usuario_id,))
    db.commit()
    cursor.close()
    flash("Situação do usuário atualizada.", "sucesso")
    return redirect(url_for("administracao.painel"))


@rotas_administracao.route("/solicitacoes-senha/<int:solicitacao_id>/concluir", methods=["POST"])
@administrador_obrigatorio
def concluir_solicitacao_senha(solicitacao_id):
    """Redefine a senha de um usuário a partir de uma solicitação pendente."""
    nova_senha = request.form.get("nova_senha", "")
    if len(nova_senha) < 6:
        flash("A senha temporária deve ter pelo menos 6 caracteres.", "perigo")
        return redirect(url_for("administracao.painel"))

    db = obter_banco()
    senha_hash = generate_password_hash(nova_senha, method="pbkdf2:sha256")
    solicitacao = concluir_solicitacao_redefinicao_senha(db, solicitacao_id, session["usuario"]["id"], senha_hash)
    if not solicitacao:
        flash("Solicitação não encontrada ou já concluída.", "perigo")
        return redirect(url_for("administracao.painel"))

    flash("Senha redefinida. Entregue a senha temporária ao usuário por um canal seguro.", "sucesso")
    return redirect(url_for("administracao.painel"))


@rotas_administracao.route("/solicitacoes-senha/<int:solicitacao_id>/cancelar", methods=["POST"])
@administrador_obrigatorio
def cancelar_solicitacao_senha(solicitacao_id):
    """Cancela uma solicitação de senha pendente sem alterar a conta."""
    db = obter_banco()
    if cancelar_solicitacao_redefinicao_senha(db, solicitacao_id, session["usuario"]["id"]):
        flash("Solicitação de senha cancelada.", "sucesso")
    else:
        flash("Solicitação não encontrada ou já tratada.", "perigo")
    return redirect(url_for("administracao.painel"))


@rotas_administracao.route("/carteirinhas/<int:carteirinha_id>/situacao", methods=["POST"])
@administrador_obrigatorio
def atualizar_situacao_carteirinha(carteirinha_id):
    """Atualiza a situação da carteirinha e notifica o paciente sobre a mudança."""

    situacao = request.form.get("situacao")
    if situacao not in ("em_analise", "ativa", "expirada", "cancelada"):
        flash("Situação de carteirinha inválida.", "perigo")
        return redirect(url_for("administracao.painel"))

    db = obter_banco()
    garantir_schema_carteirinha(db)
    cursor = db.cursor()
    cursor.execute(
        """
        SELECT pm.*, p.usuario_id, mp.nome as nome_plano
        FROM carteirinhas_pacientes pm
        JOIN pacientes p ON pm.paciente_id = p.id
        JOIN planos_carteirinha mp ON pm.plano_id = mp.id
        WHERE pm.id = %s
        """,
        (carteirinha_id,),
    )
    carteirinha = cursor.fetchone()
    if not carteirinha:
        cursor.close()
        flash("Carteirinha não encontrada.", "perigo")
        return redirect(url_for("administracao.painel"))

    if situacao == "ativa":
        cursor.execute(
            """
            UPDATE carteirinhas_pacientes
            SET situacao = 'ativa',
                inicio_em = COALESCE(inicio_em, CURDATE()),
                expira_em = COALESCE(expira_em, CURDATE() + INTERVAL 1 YEAR)
            WHERE id = %s
            """,
            (carteirinha_id,),
        )
        mensagem = f"Sua carteirinha {carteirinha['numero_carteirinha']} foi ativada no plano {carteirinha['nome_plano']}."
        tipo_notificacao = "sucesso"
    else:
        cursor.execute("UPDATE carteirinhas_pacientes SET situacao = %s WHERE id = %s", (situacao, carteirinha_id))
        mensagem = f"Sua carteirinha {carteirinha['numero_carteirinha']} mudou para a situação {rotulo_situacao_carteirinha(situacao).lower()}."
        tipo_notificacao = "informacao" if situacao == "em_analise" else "atencao"

    cursor.execute(
        """
        INSERT INTO notificacoes (usuario_id, titulo, mensagem, tipo)
        VALUES (%s, 'Carteirinha CardioLab Care', %s, %s)
        """,
        (carteirinha["usuario_id"], mensagem, tipo_notificacao),
    )
    db.commit()
    cursor.close()
    flash("Situação da carteirinha atualizada.", "sucesso")
    return redirect(url_for("administracao.painel"))


@rotas_administracao.route("/configuracoes", methods=["POST"])
@administrador_obrigatorio
def salvar_configuracoes():
    """Salva configurações básicas da clínica usando chave e valor no banco."""

    db = obter_banco()
    cursor = db.cursor()
    campos = {
        "nome_clinica": "nome_clinica",
        "whatsapp_clinica": "whatsapp_clinica",
        "horario_funcionamento": "horario_funcionamento",
        "logo_clinica": "logo_clinica",
    }
    for chave, campo in campos.items():
        valor = request.form.get(campo, "")
        cursor.execute(
            """
            INSERT INTO configuracoes_clinica (chave, valor)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE valor = VALUES(valor)
            """,
            (chave, valor),
        )
    db.commit()
    cursor.close()
    flash("Configurações salvas.", "sucesso")
    return redirect(url_for("administracao.painel"))


@rotas_administracao.route("/relatorios/<nome_relatorio>.csv")
@administrador_obrigatorio
def exportar_relatorio(nome_relatorio):
    """Gera relatórios CSV permitidos para consultas, exames e carteirinhas."""

    consultas_sql = {
        "consultas": "SELECT * FROM consultas ORDER BY data_consulta DESC",
        "exames": "SELECT * FROM resultados_exames ORDER BY criado_em DESC",
        "pacientes_novos": "SELECT p.*, u.nome, u.email FROM pacientes p JOIN usuarios u ON p.usuario_id = u.id ORDER BY p.criado_em DESC",
        "cancelamentos": "SELECT * FROM consultas WHERE situacao = 'cancelada' ORDER BY data_consulta DESC",
        "convenios": """
            SELECT pm.numero_carteirinha, pm.situacao, pm.inicio_em, pm.expira_em, mp.nome as nome_plano,
                   u.nome as nome_paciente, u.email
            FROM carteirinhas_pacientes pm
            JOIN planos_carteirinha mp ON pm.plano_id = mp.id
            JOIN pacientes p ON pm.paciente_id = p.id
            JOIN usuarios u ON p.usuario_id = u.id
            ORDER BY pm.criado_em DESC
        """,
    }
    if nome_relatorio not in consultas_sql:
        flash("Relatório inexistente.", "perigo")
        return redirect(url_for("administracao.painel"))

    db = obter_banco()
    garantir_schema_carteirinha(db)
    cursor = db.cursor()
    cursor.execute(consultas_sql[nome_relatorio])
    linhas = cursor.fetchall()
    cursor.close()

    saida = io.StringIO()
    if linhas:
        escritor = csv.DictWriter(saida, fieldnames=list(linhas[0].keys()))
        escritor.writeheader()
        escritor.writerows(linhas)
    return Response(
        saida.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={nome_relatorio}.csv"},
    )