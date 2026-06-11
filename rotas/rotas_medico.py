"""
CardioLab - rotas do médico.
Painel, agenda, pacientes, prontuário, exames e teleconsulta.
"""

import logging
import os
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from flask import Blueprint, current_app, flash, jsonify, redirect, render_template, request, session, url_for
from functools import wraps
from werkzeug.utils import secure_filename as nome_seguro_arquivo

from extensoes import obter_banco
from servicos.rotulos import rotulo_situacao_consulta
from servicos.carteirinha import garantir_schema_carteirinha
from servicos.fotos import salvar_foto_perfil
from servicos.conteudo_publico import completar_fotos_medicos


rotas_medico = Blueprint("medico", __name__, url_prefix="/medico")
logger = logging.getLogger(__name__)


def medico_obrigatorio(f):
    """Protege rotas usadas por médicos e administradores autenticados."""

    @wraps(f)
    def decorated(*args, **kwargs):
        """Valida sessão e perfil antes de executar a rota médica."""

        if "usuario" not in session:
            flash("Faça login para acessar esta página.", "atencao")
            return redirect(url_for("autenticacao.entrar"))
        if session["usuario"]["perfil"] not in ("medico", "administrador"):
            flash("Acesso restrito a médicos.", "perigo")
            return redirect(url_for("publico.inicio"))
        return f(*args, **kwargs)

    return decorated


def obter_medico_id(usuario_id):
    """Localiza o cadastro médico ligado ao usuário logado."""

    db = obter_banco()
    cursor = db.cursor()
    cursor.execute("SELECT id FROM medicos WHERE usuario_id = %s", (usuario_id,))
    resultado = cursor.fetchone()
    cursor.close()
    return resultado["id"] if resultado else None


@rotas_medico.route("/painel")
@medico_obrigatorio
def painel():
    """Renderiza o painel médico na aba solicitada pela URL."""

    aba_ativa = request.args.get("aba", "hoje")
    if aba_ativa not in ("hoje", "semana", "pacientes", "prontuarios", "metricas"):
        aba_ativa = "hoje"
    contexto = montar_contexto_painel(aba_ativa)
    if not contexto:
        flash("Perfil de médico não encontrado.", "perigo")
        return redirect(url_for("publico.inicio"))
    return render_template("painel_medico_prontuarios.html", **contexto)


def montar_contexto_painel(aba_ativa="hoje"):
    """Reúne agenda, pacientes, métricas, alertas e notificações do médico."""

    usuario = session["usuario"]
    db = obter_banco()
    garantir_schema_carteirinha(db)
    cursor = db.cursor()
    medico_id = obter_medico_id(usuario["id"])
    if not medico_id:
        cursor.close()
        return None

    cursor.execute(
        """
        SELECT d.*, u.nome, u.email, u.foto_perfil
        FROM medicos d
        JOIN usuarios u ON d.usuario_id = u.id
        WHERE d.id = %s
        """,
        (medico_id,),
    )
    linha_medico = cursor.fetchone()
    medico = completar_fotos_medicos([linha_medico])[0] if linha_medico else None

    hoje = date.today()
    cursor.execute(sql_agenda_dia("AND a.data_consulta = %s"), (medico_id, hoje))
    consultas_hoje = cursor.fetchall()

    fim_semana = hoje + timedelta(days=6)
    cursor.execute(
        sql_agenda_dia(
            """
            AND a.data_consulta BETWEEN %s AND %s
            AND a.situacao NOT IN ('cancelada', 'faltou')
            """
        ),
        (medico_id, hoje, fim_semana),
    )
    consultas_semana = cursor.fetchall()

    cursor.execute(
        """
        SELECT rc.*, u.nome as nome_paciente, p.telefone as telefone_paciente, p.id as paciente_id
        FROM calculos_risco rc
        JOIN pacientes p ON rc.paciente_id = p.id
        JOIN usuarios u ON p.usuario_id = u.id
        WHERE rc.classe_risco = 'alto'
        ORDER BY rc.calculado_em DESC
        LIMIT 8
        """
    )
    pacientes_criticos = cursor.fetchall()

    cursor.execute(
        """
        SELECT
            COUNT(CASE WHEN situacao = 'agendada' THEN 1 END) as agendadas,
            COUNT(CASE WHEN situacao = 'confirmada' THEN 1 END) as confirmadas,
            COUNT(CASE WHEN situacao = 'finalizada' THEN 1 END) as finalizadas,
            COUNT(CASE WHEN situacao = 'cancelada' THEN 1 END) as canceladas
        FROM consultas
        WHERE medico_id = %s AND data_consulta >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
        """,
        (medico_id,),
    )
    estatisticas = cursor.fetchone()

    cursor.execute(
        """
        SELECT
            COUNT(CASE WHEN MONTH(data_consulta) = MONTH(CURDATE()) AND situacao = 'finalizada' THEN 1 END) as consultas_mes,
            ROUND(100 * COUNT(CASE WHEN situacao = 'cancelada' THEN 1 END) / NULLIF(COUNT(*), 0), 1) as taxa_cancelamento,
            (SELECT ROUND(AVG(nota), 1) FROM respostas_nps) as media_nps,
            ROUND(AVG(duracao_minutos), 0) as minutos_medios
        FROM consultas
        WHERE medico_id = %s AND data_consulta >= DATE_SUB(CURDATE(), INTERVAL 90 DAY)
        """,
        (medico_id,),
    )
    metricas_medico = cursor.fetchone()

    cursor.execute(
        """
        SELECT * FROM notificacoes
        WHERE usuario_id = %s AND lida = 0
        ORDER BY criado_em DESC
        LIMIT 10
        """,
        (usuario["id"],),
    )
    notificacoes = cursor.fetchall()

    cursor.execute(
        """
            SELECT DISTINCT u.nome as nome_paciente, u.foto_perfil as foto_paciente, p.telefone, p.data_nascimento, p.id as paciente_id,
               pm.numero_carteirinha as numero_carteirinha,
               pm.situacao as situacao_carteirinha,
               mp.nome as nome_plano_carteirinha,
               (SELECT MAX(a2.data_consulta)
                FROM consultas a2
                WHERE a2.paciente_id = p.id AND a2.medico_id = %s) as ultima_consulta
        FROM consultas a
        JOIN pacientes p ON a.paciente_id = p.id
        JOIN usuarios u ON p.usuario_id = u.id
        LEFT JOIN carteirinhas_pacientes pm
               ON pm.paciente_id = p.id
              AND pm.situacao IN ('ativa', 'em_analise')
              AND (pm.expira_em IS NULL OR pm.expira_em >= CURDATE())
        LEFT JOIN planos_carteirinha mp ON mp.id = pm.plano_id
        WHERE a.medico_id = %s
        ORDER BY u.nome
        """,
        (medico_id, medico_id),
    )
    lista_pacientes = cursor.fetchall()

    cursor.close()
    total_carteirinhas_ativas = sum(
        1 for consulta in consultas_hoje if consulta.get("situacao_carteirinha") == "ativa"
    )
    return {
        "medico": medico,
        "consultas_hoje": consultas_hoje,
        "consultas_semana": consultas_semana,
        "pacientes_criticos": pacientes_criticos,
        "estatisticas": estatisticas,
        "metricas_medico": metricas_medico,
        "notificacoes": notificacoes,
        "lista_pacientes": lista_pacientes,
        "total_carteirinhas_ativas": total_carteirinhas_ativas,
        "hoje": hoje,
        "dias_semana": [hoje + timedelta(days=i) for i in range(7)],
        "aba_ativa": aba_ativa,
    }


@rotas_medico.route("/perfil/foto", methods=["POST"])
@medico_obrigatorio
def atualizar_foto_perfil():
    """Salva nova foto do médico e atualiza a sessão usada no cabeçalho."""

    usuario = session["usuario"]
    try:
        url_foto = salvar_foto_perfil(
            request.files.get("foto_perfil"),
            current_app.config["PASTA_ARQUIVOS"],
            usuario["id"],
        )
        db = obter_banco()
        cursor = db.cursor()
        cursor.execute("UPDATE usuarios SET foto_perfil = %s WHERE id = %s", (url_foto, usuario["id"]))
        db.commit()
        cursor.close()
        session["usuario"]["foto_perfil"] = url_foto
        flash("Foto atualizada com sucesso.", "sucesso")
    except ValueError as erro:
        flash(str(erro), "perigo")
    except Exception:
        logger.exception("atualizacao_foto_medico_falhou", extra={"extra": {"usuario_id": usuario["id"]}})
        flash("Não foi possível atualizar sua foto agora.", "perigo")
    return redirect(url_for("medico.painel"))


def sql_agenda_dia(extra_where):
    """Monta a consulta SQL base da agenda com filtros extras reaproveitáveis."""

    return f"""
        SELECT a.*, s.nome as nome_servico, u.nome as nome_paciente, u.foto_perfil as foto_paciente, p.telefone as telefone_paciente,
               p.id as paciente_id,
               pm.numero_carteirinha as numero_carteirinha,
               pm.situacao as situacao_carteirinha,
               mp.nome as nome_plano_carteirinha,
               mp.codigo as codigo_plano_carteirinha,
               COALESCE(
                   (SELECT rc2.classe_risco
                    FROM calculos_risco rc2
                    WHERE rc2.paciente_id = p.id
                    ORDER BY rc2.calculado_em DESC
                    LIMIT 1),
                   (SELECT mr2.alerta_risco
                    FROM prontuarios mr2
                    WHERE mr2.paciente_id = p.id
                    ORDER BY mr2.criado_em DESC
                    LIMIT 1)
               ) as alerta_risco
        FROM consultas a
        JOIN servicos s ON a.servico_id = s.id
        JOIN pacientes p ON a.paciente_id = p.id
        JOIN usuarios u ON p.usuario_id = u.id
        LEFT JOIN carteirinhas_pacientes pm
               ON pm.paciente_id = p.id
              AND pm.situacao IN ('ativa', 'em_analise')
              AND (pm.expira_em IS NULL OR pm.expira_em >= CURDATE())
        LEFT JOIN planos_carteirinha mp ON mp.id = pm.plano_id
        WHERE a.medico_id = %s {extra_where}
        ORDER BY a.data_consulta, COALESCE(a.posicao_fila, 9999), a.horario_consulta
    """


@rotas_medico.route("/agenda")
@medico_obrigatorio
def agenda():
    """Redireciona o atalho de agenda para a aba Hoje do painel médico."""

    return redirect(url_for("medico.painel", aba="hoje"))


@rotas_medico.route("/pacientes")
@medico_obrigatorio
def pacientes():
    """Abre o painel médico diretamente na aba de pacientes."""

    contexto = montar_contexto_painel("pacientes")
    if not contexto:
        flash("Perfil de médico não encontrado.", "perigo")
        return redirect(url_for("publico.inicio"))
    return render_template("painel_medico_prontuarios.html", **contexto)


@rotas_medico.route("/prontuarios/<int:paciente_id>")
@medico_obrigatorio
def prontuario_paciente(paciente_id):
    """Carrega prontuário completo do paciente dentro do painel médico."""

    dados = carregar_prontuario_paciente(paciente_id)
    if not dados.get("paciente"):
        flash("Paciente não encontrado.", "perigo")
        return redirect(url_for("medico.painel"))
    contexto = montar_contexto_painel("prontuarios")
    if not contexto:
        flash("Perfil de médico não encontrado.", "perigo")
        return redirect(url_for("publico.inicio"))
    return render_template("painel_medico_prontuarios.html", mostrar_prontuario=True, **contexto, **dados)


@rotas_medico.route("/api/pacientes/<int:paciente_id>")
@medico_obrigatorio
def api_prontuario_paciente(paciente_id):
    """Entrega prontuário em JSON para o painel lateral do médico."""

    dados = carregar_prontuario_paciente(paciente_id)
    if not dados.get("paciente"):
        return jsonify({"erro": "nao_encontrado"}), 404
    return jsonify(json_seguro(dados))


def json_seguro(valor):
    """Converte datas, horários e decimais em valores seguros para JSON."""

    if isinstance(valor, dict):
        return {chave: json_seguro(item) for chave, item in valor.items()}
    if isinstance(valor, (list, tuple)):
        return [json_seguro(item) for item in valor]
    if isinstance(valor, (date, datetime, time)):
        return valor.isoformat()
    if isinstance(valor, timedelta):
        total = int(valor.total_seconds())
        return f"{total // 3600:02d}:{(total % 3600) // 60:02d}"
    if isinstance(valor, Decimal):
        return float(valor)
    return valor


def carregar_prontuario_paciente(paciente_id):
    """Busca dados clínicos do paciente e bloqueia acesso sem vínculo de consulta."""

    usuario = session["usuario"]
    db = obter_banco()
    garantir_schema_carteirinha(db)
    cursor = db.cursor()
    medico_id = obter_medico_id(usuario["id"])

    cursor.execute(
        """
        SELECT p.*, u.nome, u.email, u.cpf, u.foto_perfil,
               pm.numero_carteirinha as numero_carteirinha,
               pm.situacao as situacao_carteirinha,
               mp.nome as nome_plano_carteirinha,
               mp.desconto_consulta_percentual,
               mp.desconto_exame_percentual
        FROM pacientes p
        JOIN usuarios u ON p.usuario_id = u.id
        LEFT JOIN carteirinhas_pacientes pm
               ON pm.paciente_id = p.id
              AND pm.situacao IN ('ativa', 'em_analise')
              AND (pm.expira_em IS NULL OR pm.expira_em >= CURDATE())
        LEFT JOIN planos_carteirinha mp ON mp.id = pm.plano_id
        WHERE p.id = %s
        """,
        (paciente_id,),
    )
    paciente = cursor.fetchone()
    if not paciente:
        cursor.close()
        return {"paciente": None}

    cursor.execute(
        "SELECT COUNT(*) as total FROM consultas WHERE medico_id = %s AND paciente_id = %s",
        (medico_id, paciente_id),
    )
    acesso = cursor.fetchone()
    if session["usuario"]["perfil"] != "administrador" and (not acesso or acesso["total"] == 0):
        cursor.close()
        return {"paciente": None}

    cursor.execute(
        """
        SELECT a.*, s.nome as nome_servico
        FROM consultas a
        JOIN servicos s ON a.servico_id = s.id
        WHERE a.paciente_id = %s AND a.medico_id = %s
        ORDER BY a.data_consulta DESC
        """,
        (paciente_id, medico_id),
    )
    consultas = cursor.fetchall()

    cursor.execute(
        """
        SELECT e.*, s.nome as nome_servico
        FROM resultados_exames e
        LEFT JOIN servicos s ON e.servico_id = s.id
        WHERE e.paciente_id = %s
        ORDER BY e.criado_em DESC
        """,
        (paciente_id,),
    )
    exames = cursor.fetchall()

    cursor.execute(
        "SELECT * FROM metricas_saude WHERE paciente_id = %s ORDER BY medido_em DESC LIMIT 10",
        (paciente_id,),
    )
    metricas_saude = cursor.fetchall()

    cursor.execute(
        """
        SELECT mr.*, u.nome as nome_medico
        FROM prontuarios mr
        JOIN medicos d ON mr.medico_id = d.id
        JOIN usuarios u ON d.usuario_id = u.id
        WHERE mr.paciente_id = %s
        ORDER BY mr.criado_em DESC
        """,
        (paciente_id,),
    )
    prontuarios = cursor.fetchall()
    cursor.close()
    return {
        "paciente": paciente,
        "consultas_paciente": consultas,
        "exames_paciente": exames,
        "metricas_saude_paciente": metricas_saude,
        "prontuarios_paciente": prontuarios,
    }


@rotas_medico.route("/consultas/<int:consulta_id>/situacao", methods=["POST"])
@medico_obrigatorio
def atualizar_situacao_consulta(consulta_id):
    """Atualiza a situação da consulta e cria notificações conforme a mudança."""

    usuario = session["usuario"]
    db = obter_banco()
    cursor = db.cursor()
    medico_id = obter_medico_id(usuario["id"])
    nova_situacao = request.form.get("situacao")
    situacoes_validas = ["agendada", "confirmada", "em_atendimento", "finalizada", "cancelada", "faltou"]
    if nova_situacao not in situacoes_validas:
        flash("Situação inválida.", "perigo")
        return redirect(url_for("medico.painel"))

    cursor.execute(
        """
        SELECT a.*, p.usuario_id as usuario_paciente_id, s.nome as nome_servico
        FROM consultas a
        JOIN pacientes p ON a.paciente_id = p.id
        JOIN servicos s ON a.servico_id = s.id
        WHERE a.id = %s AND a.medico_id = %s
        """,
        (consulta_id, medico_id),
    )
    consulta = cursor.fetchone()
    if not consulta:
        flash("Consulta não encontrada.", "perigo")
        cursor.close()
        return redirect(url_for("medico.painel"))

    motivo = request.form.get("motivo", "")
    url_sala = consulta.get("sala_teleconsulta_url")
    if nova_situacao == "confirmada" and "teleconsulta" in consulta["nome_servico"].lower():
        url_sala = f"https://meet.jit.si/cardiolab-{consulta_id}"

    cursor.execute(
        """
        UPDATE consultas
        SET situacao = %s,
            motivo_cancelamento = %s,
            sala_teleconsulta_url = COALESCE(%s, sala_teleconsulta_url),
            confirmada_em = CASE WHEN %s = 'confirmada' THEN NOW() ELSE confirmada_em END
        WHERE id = %s
        """,
        (nova_situacao, motivo if nova_situacao == "cancelada" else None, url_sala, nova_situacao, consulta_id),
    )

    if nova_situacao == "cancelada":
        cursor.execute(
            """
            INSERT INTO notificacoes (usuario_id, titulo, mensagem, tipo)
            VALUES (%s, 'Consulta Cancelada', %s, 'perigo')
            """,
            (
                consulta["usuario_paciente_id"],
                f"Sua consulta do dia {consulta['data_consulta']} foi cancelada. Motivo: {motivo}",
            ),
        )
    if nova_situacao == "finalizada":
        cursor.execute(
            """
            INSERT INTO notificacoes (usuario_id, titulo, mensagem, tipo)
            VALUES (%s, 'Avalie seu Atendimento',
                    'De 0 a 10, quanto você indicaria a CardioLab? Acesse o portal para avaliar.', 'informacao')
            """,
            (consulta["usuario_paciente_id"],),
        )

    db.commit()
    cursor.close()
    flash(f"Situação atualizada para: {rotulo_situacao_consulta(nova_situacao).lower()}", "sucesso")
    return redirect(url_for("medico.painel"))


@rotas_medico.route("/fila/reordenar", methods=["POST"])
@medico_obrigatorio
def reordenar_fila():
    """Persiste a sequência da fila de atendimento definida pelo médico."""

    usuario = session["usuario"]
    medico_id = obter_medico_id(usuario["id"])
    ids_consultas = (request.get_json() or {}).get("ids_consultas", [])
    db = obter_banco()
    cursor = db.cursor()
    for posicao, consulta_id in enumerate(ids_consultas, start=1):
        cursor.execute(
            "UPDATE consultas SET posicao_fila = %s WHERE id = %s AND medico_id = %s",
            (posicao, consulta_id, medico_id),
        )
    db.commit()
    cursor.close()
    return jsonify({"sucesso": True})


@rotas_medico.route("/exames/enviar", methods=["POST"])
@medico_obrigatorio
def enviar_exame():
    """Recebe laudo enviado pelo médico, salva arquivo e notifica o paciente."""

    usuario = session["usuario"]
    medico_id = obter_medico_id(usuario["id"])
    paciente_id = request.form.get("paciente_id")
    servico_id = request.form.get("servico_id") or None
    titulo = request.form.get("titulo", "Laudo cardiológico").strip()
    arquivo = request.files.get("arquivo")
    if not arquivo or not paciente_id:
        flash("Informe paciente e arquivo.", "perigo")
        return redirect(url_for("medico.painel"))

    nome_arquivo = nome_seguro_arquivo(arquivo.filename)
    pasta_envio = os.path.join(current_app.config["PASTA_ARQUIVOS"], "exames")
    os.makedirs(pasta_envio, exist_ok=True)
    caminho_arquivo = os.path.join(pasta_envio, nome_arquivo)
    arquivo.save(caminho_arquivo)
    arquivo_url = url_for("static", filename=f"arquivos_enviados/exames/{nome_arquivo}")
    tipo_resultado = "pdf" if nome_arquivo.lower().endswith(".pdf") else "imagem"

    db = obter_banco()
    cursor = db.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO resultados_exames
                (paciente_id, medico_id, servico_id, titulo, arquivo_url, tipo_resultado, assinatura_digital)
            VALUES (%s, %s, %s, %s, %s, %s,
                    (SELECT CONCAT(u.nome, ' - ', d.crm) FROM medicos d JOIN usuarios u ON d.usuario_id = u.id WHERE d.id = %s))
            """,
            (paciente_id, medico_id, servico_id, titulo, arquivo_url, tipo_resultado, medico_id),
        )
        cursor.execute(
            """
            INSERT INTO notificacoes (usuario_id, titulo, mensagem, tipo)
            SELECT p.usuario_id, 'Exame disponível', %s, 'sucesso' FROM pacientes p WHERE p.id = %s
            """,
            (f"O resultado {titulo} está disponível no portal.", paciente_id),
        )
        db.commit()
        flash("Laudo enviado com sucesso.", "sucesso")
    except Exception:
        db.rollback()
        logger.exception("envio_exame_falhou", extra={"extra": {"paciente_id": paciente_id}})
        flash("Erro ao enviar laudo.", "perigo")
    finally:
        cursor.close()
    return redirect(url_for("medico.painel"))


@rotas_medico.route("/exames")
@medico_obrigatorio
def exames():
    """Redireciona o atalho de exames para o painel médico."""

    return redirect(url_for("medico.painel"))





