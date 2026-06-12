"""
CardioLab - rotas do médico.
Painel, agenda e contexto geral.
Rotas de prontuários e ações ficam em módulos separados.
"""

import logging
from datetime import date, timedelta

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from functools import wraps

from extensoes import obter_banco
from servicos.carteirinha import garantir_schema_carteirinha
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
            (SELECT ROUND(AVG(nota), 1) FROM avaliacoes WHERE tipo = 'nps') as media_nps,
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


# ============================================================
# Registra rotas de sub-módulos no mesmo blueprint
# ============================================================
import rotas.rotas_medico_prontuarios  # noqa: E402, F401
import rotas.rotas_medico_acoes        # noqa: E402, F401
