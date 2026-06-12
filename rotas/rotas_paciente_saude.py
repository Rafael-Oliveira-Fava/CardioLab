"""
CardioLab - rotas de saúde do paciente.
Cálculo de risco cardiovascular e métricas de saúde.
"""

import json
import logging

from flask import jsonify, redirect, request, session, url_for

from extensoes import obter_banco
from servicos.risco import calcular_risco_framingham
from rotas.rotas_paciente import rotas_paciente, paciente_obrigatorio, obter_paciente_id


logger = logging.getLogger(__name__)


@rotas_paciente.route("/api/calculos-risco", methods=["POST"])
@paciente_obrigatorio
def api_salvar_calculo_risco():
    """Calcula, salva e retorna o risco cardiovascular informado pelo paciente."""

    usuario = session["usuario"]
    dados = request.get_json() or {}
    try:
        resultado = calcular_risco_framingham(
            sexo=dados.get("sexo"),
            idade=int(dados.get("idade")),
            colesterol_total=float(dados.get("colesterol_total")),
            hdl=float(dados.get("hdl")),
            pressao_sistolica=float(dados.get("pressao_sistolica")),
            trata_pressao=bool(dados.get("trata_pressao")),
            fumante=bool(dados.get("fumante")),
            diabetes=bool(dados.get("diabetes")),
        )
    except (TypeError, ValueError) as erro:
        return jsonify({"erro": str(erro)}), 400

    db = obter_banco()
    cursor = db.cursor()
    paciente_id = obter_paciente_id(usuario["id"])
    cursor.execute(
        """
        INSERT INTO calculos_risco
            (paciente_id, sexo, idade, colesterol_total, hdl, pressao_sistolica, trata_pressao, fumante, diabetes,
             risco_percentual, classe_risco, recomendacoes_json)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            paciente_id,
            dados.get("sexo"),
            dados.get("idade"),
            dados.get("colesterol_total"),
            dados.get("hdl"),
            dados.get("pressao_sistolica"),
            int(bool(dados.get("trata_pressao"))),
            int(bool(dados.get("fumante"))),
            int(bool(dados.get("diabetes"))),
            resultado["risco_percentual"],
            resultado["classe_risco"],
            json.dumps(resultado["recomendacoes"], ensure_ascii=False),
        ),
    )
    cursor.execute(
        """
        INSERT INTO prontuarios (paciente_id, medico_id, observacoes, alerta_risco)
        SELECT %s, d.id, %s, %s FROM medicos d ORDER BY d.id LIMIT 1
        """,
        (paciente_id, f"Cálculo Framingham: {resultado['risco_percentual']}% em 10 anos.", resultado["classe_risco"]),
    )
    db.commit()
    cursor.close()
    return jsonify(resultado)


@rotas_paciente.route("/api/metricas-saude")
@paciente_obrigatorio
def api_metricas_saude():
    """Entrega métricas de saúde do paciente em JSON para gráficos do painel."""

    usuario = session["usuario"]
    db = obter_banco()
    cursor = db.cursor()
    paciente_id = obter_paciente_id(usuario["id"])
    cursor.execute(
        """
        SELECT pressao_arterial, frequencia_cardiaca, peso, imc, glicemia, colesterol,
               DATE_FORMAT(medido_em, '%%Y-%%m-%%d') as data
        FROM metricas_saude
        WHERE paciente_id = %s
        ORDER BY medido_em ASC
        """,
        (paciente_id,),
    )
    metricas = cursor.fetchall()
    cursor.close()
    return jsonify(metricas)


@rotas_paciente.route("/saude")
@paciente_obrigatorio
def saude():
    """Redireciona o atalho de saúde para a aba correspondente do painel."""

    return redirect(url_for("paciente.painel"))


@rotas_paciente.route("/calculadora-risco")
@paciente_obrigatorio
def calculadora_risco():
    """Redireciona o atalho da calculadora para a aba de saúde do painel."""

    return redirect(url_for("paciente.painel"))
