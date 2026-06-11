import json
from datetime import date, timedelta
from uuid import uuid4


PLANOS_PADRAO = [
    {
        "codigo": "CARE-ESSENCIAL",
        "nome": "CardioLab Care Essencial",
        "valor_mensal": 39.90,
        "desconto_consulta_percentual": 10,
        "desconto_exame_percentual": 8,
        "encaixes_urgentes_mes": 0,
        "teleconsultas_mes": 0,
        "descricao": "Plano de entrada para acompanhamento preventivo e descontos básicos.",
        "beneficios": [
            "Carteirinha digital CardioLab",
            "10% em consultas particulares",
            "8% em exames cardiológicos",
            "Histórico unificado no portal",
        ],
    },
    {
        "codigo": "CARE-PLUS",
        "nome": "CardioLab Care Plus",
        "valor_mensal": 69.90,
        "desconto_consulta_percentual": 20,
        "desconto_exame_percentual": 15,
        "encaixes_urgentes_mes": 1,
        "teleconsultas_mes": 1,
        "descricao": "Convênio interno para pacientes em acompanhamento recorrente.",
        "beneficios": [
            "20% em consultas particulares",
            "15% em exames cardiológicos",
            "1 encaixe prioritário por mês",
            "1 teleconsulta de retorno por mês",
        ],
    },
    {
        "codigo": "CARE-PREMIUM",
        "nome": "CardioLab Care Premium",
        "valor_mensal": 129.90,
        "desconto_consulta_percentual": 35,
        "desconto_exame_percentual": 25,
        "encaixes_urgentes_mes": 2,
        "teleconsultas_mes": 2,
        "descricao": "Cobertura premium para controle cardiológico contínuo.",
        "beneficios": [
            "35% em consultas particulares",
            "25% em exames cardiológicos",
            "2 encaixes prioritários por mês",
            "2 teleconsultas de retorno por mês",
        ],
    },
]

_schema_checked = False


def garantir_schema_carteirinha(banco):
    """Garante que tabelas e planos padrão da carteirinha existam no banco."""
    global _schema_checked
    if _schema_checked:
        return

    cursor = banco.cursor()
    try:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS planos_carteirinha (
                id INT AUTO_INCREMENT PRIMARY KEY,
                codigo VARCHAR(40) NOT NULL UNIQUE,
                nome VARCHAR(120) NOT NULL,
                valor_mensal DECIMAL(10,2) NOT NULL DEFAULT 0,
                desconto_consulta_percentual DECIMAL(5,2) NOT NULL DEFAULT 0,
                desconto_exame_percentual DECIMAL(5,2) NOT NULL DEFAULT 0,
                encaixes_urgentes_mes INT NOT NULL DEFAULT 0,
                teleconsultas_mes INT NOT NULL DEFAULT 0,
                descricao TEXT,
                beneficios_json TEXT,
                ativo TINYINT(1) DEFAULT 1,
                criado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_planos_carteirinha_codigo (codigo),
                INDEX idx_planos_carteirinha_ativo (ativo)
            ) ENGINE=InnoDB
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS carteirinhas_pacientes (
                id INT AUTO_INCREMENT PRIMARY KEY,
                paciente_id INT NOT NULL,
                plano_id INT NOT NULL,
                numero_carteirinha VARCHAR(40) NOT NULL UNIQUE,
                titular VARCHAR(200),
                situacao ENUM('em_analise','ativa','expirada','cancelada') NOT NULL DEFAULT 'em_analise',
                inicio_em DATE,
                expira_em DATE,
                criado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
                atualizado_em DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (paciente_id) REFERENCES pacientes(id) ON DELETE CASCADE,
                FOREIGN KEY (plano_id) REFERENCES planos_carteirinha(id) ON DELETE RESTRICT,
                INDEX idx_carteirinhas_paciente (paciente_id),
                INDEX idx_carteirinhas_situacao (situacao),
                INDEX idx_carteirinhas_numero (numero_carteirinha)
            ) ENGINE=InnoDB
            """
        )
        for plano in PLANOS_PADRAO:
            cursor.execute(
                """
                INSERT INTO planos_carteirinha
                    (codigo, nome, valor_mensal, desconto_consulta_percentual, desconto_exame_percentual,
                     encaixes_urgentes_mes, teleconsultas_mes, descricao, beneficios_json, ativo)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 1)
                ON DUPLICATE KEY UPDATE
                    nome = VALUES(nome),
                    valor_mensal = VALUES(valor_mensal),
                    desconto_consulta_percentual = VALUES(desconto_consulta_percentual),
                    desconto_exame_percentual = VALUES(desconto_exame_percentual),
                    encaixes_urgentes_mes = VALUES(encaixes_urgentes_mes),
                    teleconsultas_mes = VALUES(teleconsultas_mes),
                    descricao = VALUES(descricao),
                    beneficios_json = VALUES(beneficios_json),
                    ativo = 1
                """,
                (
                    plano["codigo"],
                    plano["nome"],
                    plano["valor_mensal"],
                    plano["desconto_consulta_percentual"],
                    plano["desconto_exame_percentual"],
                    plano["encaixes_urgentes_mes"],
                    plano["teleconsultas_mes"],
                    plano["descricao"],
                    json.dumps(plano["beneficios"], ensure_ascii=False),
                ),
            )
        banco.commit()
        _schema_checked = True
    except Exception:
        banco.rollback()
        raise
    finally:
        cursor.close()


def hidratar_plano(linha):
    """Converte o JSON de benefícios de um plano para lista Python."""
    if not linha:
        return linha
    linha.setdefault("codigo_plano", linha.get("codigo"))
    linha.setdefault("nome_plano", linha.get("nome"))
    linha["beneficios"] = []
    if linha.get("beneficios_json"):
        try:
            linha["beneficios"] = json.loads(linha["beneficios_json"])
        except (TypeError, ValueError):
            linha["beneficios"] = []
    return linha


def listar_planos_carteirinha(cursor):
    """Lista planos ativos de carteirinha ordenados pelo preço mensal."""
    cursor.execute(
        """
        SELECT *
        FROM planos_carteirinha
        WHERE ativo = 1
        ORDER BY valor_mensal
        """
    )
    return [hidratar_plano(linha) for linha in cursor.fetchall()]


def buscar_carteirinha_paciente(cursor, paciente_id):
    """Busca a carteirinha ativa ou pendente mais relevante de um paciente."""
    cursor.execute(
        """
        SELECT pm.*,
               mp.codigo as codigo_plano, mp.nome as nome_plano, mp.valor_mensal,
               mp.desconto_consulta_percentual, mp.desconto_exame_percentual,
               mp.encaixes_urgentes_mes, mp.teleconsultas_mes,
               mp.descricao, mp.beneficios_json
        FROM carteirinhas_pacientes pm
        JOIN planos_carteirinha mp ON pm.plano_id = mp.id
        WHERE pm.paciente_id = %s
          AND pm.situacao IN ('em_analise', 'ativa')
          AND (pm.expira_em IS NULL OR pm.expira_em >= CURDATE())
        ORDER BY FIELD(pm.situacao, 'ativa', 'em_analise'), pm.criado_em DESC
        LIMIT 1
        """,
        (paciente_id,),
    )
    return hidratar_plano(cursor.fetchone())


def gerar_numero_carteirinha(paciente_id):
    """Cria número único de carteirinha com mês, paciente e sufixo aleatório."""
    return f"CLB-{date.today():%y%m}-{int(paciente_id):05d}-{uuid4().hex[:4].upper()}"


def solicitar_carteirinha(banco, paciente_id, plano_id, titular):
    """Solicita uma nova carteirinha pendente para paciente sem cobertura."""
    garantir_schema_carteirinha(banco)
    cursor = banco.cursor()
    try:
        existente = buscar_carteirinha_paciente(cursor, paciente_id)
        if existente:
            return None, "Este paciente já possui uma carteirinha ativa ou em análise."

        cursor.execute(
            "SELECT id, nome FROM planos_carteirinha WHERE id = %s AND ativo = 1",
            (plano_id,),
        )
        plano = cursor.fetchone()
        if not plano:
            return None, "Plano CardioLab Care não encontrado."

        numero_carteirinha = gerar_numero_carteirinha(paciente_id)
        validade = date.today() + timedelta(days=365)
        cursor.execute(
            """
            INSERT INTO carteirinhas_pacientes
                (paciente_id, plano_id, numero_carteirinha, titular, situacao, inicio_em, expira_em)
            VALUES (%s, %s, %s, %s, 'em_analise', CURDATE(), %s)
            """,
            (paciente_id, plano_id, numero_carteirinha, titular, validade),
        )
        banco.commit()
        return {"numero_carteirinha": numero_carteirinha, "nome_plano": plano["nome"], "situacao": "em_analise"}, None
    except Exception:
        banco.rollback()
        raise
    finally:
        cursor.close()

