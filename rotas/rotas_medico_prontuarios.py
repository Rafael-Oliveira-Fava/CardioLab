"""
CardioLab - rotas de prontuários do médico.
Visualização de pacientes e prontuários clínicos.
"""

import logging
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from flask import flash, jsonify, redirect, render_template, request, session, url_for

from extensoes import obter_banco
from servicos.carteirinha import garantir_schema_carteirinha
from rotas.rotas_medico import rotas_medico, medico_obrigatorio, obter_medico_id, montar_contexto_painel


logger = logging.getLogger(__name__)


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
