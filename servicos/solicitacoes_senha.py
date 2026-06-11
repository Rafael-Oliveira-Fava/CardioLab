"""Solicitações administrativas para troca de senha."""

from servicos.cpf import limpar_cpf, formatar_cpf
from servicos.usuarios import normalizar_email


SITUACAO_SOLICITACAO_PENDENTE = "pendente"
SITUACAO_SOLICITACAO_CONCLUIDA = "concluida"
SITUACAO_SOLICITACAO_CANCELADA = "cancelada"


def garantir_tabela_solicitacoes_senha(banco):
    """Cria a tabela de solicitações de senha quando ela ainda não existe."""
    cursor = banco.cursor()
    try:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS solicitacoes_senha (
                id INT AUTO_INCREMENT PRIMARY KEY,
                usuario_id INT NOT NULL,
                identificador VARCHAR(200) NOT NULL,
                situacao ENUM('pendente','concluida','cancelada') NOT NULL DEFAULT 'pendente',
                ip_solicitante VARCHAR(80),
                resolvido_por INT,
                resolvido_em DATETIME,
                criado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
                atualizado_em DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
                FOREIGN KEY (resolvido_por) REFERENCES usuarios(id) ON DELETE SET NULL,
                INDEX idx_solicitacoes_senha_usuario (usuario_id),
                INDEX idx_solicitacoes_senha_situacao (situacao),
                INDEX idx_solicitacoes_senha_criada (criado_em)
            ) ENGINE=InnoDB
            """
        )
        banco.commit()
    finally:
        cursor.close()


def buscar_usuario_por_identificador(cursor, identificador):
    """Busca usuário ativo pelo e-mail normalizado ou CPF formatado."""
    email = normalizar_email(identificador)
    cpf_limpo = limpar_cpf(identificador)
    cpf = formatar_cpf(cpf_limpo) if len(cpf_limpo) == 11 else (identificador or "").strip()
    cursor.execute(
        """
        SELECT id, nome, email, cpf
        FROM usuarios
        WHERE ativo = 1
          AND (LOWER(email) = %s OR cpf = %s)
        LIMIT 1
        """,
        (email, cpf),
    )
    return cursor.fetchone()


def criar_solicitacao_redefinicao_senha(banco, identificador, ip_solicitante=None):
    """Registra pedido para o administrador redefinir a senha de um usuário."""
    garantir_tabela_solicitacoes_senha(banco)
    cursor = banco.cursor()
    try:
        usuario = buscar_usuario_por_identificador(cursor, identificador)
        if not usuario:
            return None, False

        cursor.execute(
            """
            SELECT id
            FROM solicitacoes_senha
            WHERE usuario_id = %s AND situacao = 'pendente'
            LIMIT 1
            """,
            (usuario["id"],),
        )
        if cursor.fetchone():
            return usuario, False

        cursor.execute(
            """
            INSERT INTO solicitacoes_senha (usuario_id, identificador, ip_solicitante)
            VALUES (%s, %s, %s)
            """,
            (usuario["id"], (identificador or "").strip(), ip_solicitante),
        )
        banco.commit()
        return usuario, True
    except Exception:
        banco.rollback()
        raise
    finally:
        cursor.close()


def listar_solicitacoes_redefinicao_senha(cursor, limite=30):
    """Lista pedidos pendentes para o painel administrativo."""
    cursor.execute(
        """
        SELECT s.*, u.nome as nome_usuario, u.email, u.cpf
        FROM solicitacoes_senha s
        JOIN usuarios u ON u.id = s.usuario_id
        WHERE s.situacao = 'pendente'
        ORDER BY s.criado_em ASC
        LIMIT %s
        """,
        (int(limite),),
    )
    return cursor.fetchall()


def concluir_solicitacao_redefinicao_senha(banco, solicitacao_id, admin_id, senha_hash):
    """Troca a senha do usuário e marca a solicitação como concluída."""
    garantir_tabela_solicitacoes_senha(banco)
    cursor = banco.cursor()
    try:
        cursor.execute(
            """
            SELECT s.id, s.usuario_id, u.nome, u.email
            FROM solicitacoes_senha s
            JOIN usuarios u ON u.id = s.usuario_id
            WHERE s.id = %s AND s.situacao = 'pendente'
            LIMIT 1
            """,
            (solicitacao_id,),
        )
        solicitacao = cursor.fetchone()
        if not solicitacao:
            return None

        cursor.execute("UPDATE usuarios SET senha_hash = %s WHERE id = %s", (senha_hash, solicitacao["usuario_id"]))
        cursor.execute(
            """
            UPDATE solicitacoes_senha
            SET situacao = 'concluida', resolvido_por = %s, resolvido_em = NOW()
            WHERE id = %s
            """,
            (admin_id, solicitacao_id),
        )
        cursor.execute(
            """
            INSERT INTO notificacoes (usuario_id, titulo, mensagem, tipo)
            VALUES (%s, 'Senha redefinida', 'Sua senha foi redefinida pela administração da CardioLab.', 'informacao')
            """,
            (solicitacao["usuario_id"],),
        )
        banco.commit()
        return solicitacao
    except Exception:
        banco.rollback()
        raise
    finally:
        cursor.close()


def cancelar_solicitacao_redefinicao_senha(banco, solicitacao_id, admin_id):
    """Cancela uma solicitação pendente sem alterar a senha do usuário."""
    garantir_tabela_solicitacoes_senha(banco)
    cursor = banco.cursor()
    try:
        cursor.execute(
            """
            UPDATE solicitacoes_senha
            SET situacao = 'cancelada', resolvido_por = %s, resolvido_em = NOW()
            WHERE id = %s AND situacao = 'pendente'
            """,
            (admin_id, solicitacao_id),
        )
        alteradas = cursor.rowcount
        banco.commit()
        return alteradas > 0
    except Exception:
        banco.rollback()
        raise
    finally:
        cursor.close()

