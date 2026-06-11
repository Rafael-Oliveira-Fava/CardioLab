import math
from datetime import date


COEFICIENTES_FRAMINGHAM = {
    "M": {
        "ln_idade": 3.06117,
        "ln_colesterol_total": 1.12370,
        "ln_hdl": -0.93263,
        "ln_pressao_tratada": 1.99881,
        "ln_pressao_nao_tratada": 1.93303,
        "fumante": 0.65451,
        "diabetes": 0.57367,
        "sobrevida_base": 0.88936,
        "media": 23.9802,
    },
    "F": {
        "ln_idade": 2.32888,
        "ln_colesterol_total": 1.20904,
        "ln_hdl": -0.70833,
        "ln_pressao_tratada": 2.82263,
        "ln_pressao_nao_tratada": 2.76157,
        "fumante": 0.52873,
        "diabetes": 0.69154,
        "sobrevida_base": 0.95012,
        "media": 26.1931,
    },
}


def idade_pela_data_nascimento(data_nascimento, hoje=None):
    """Calcula idade completa a partir da data de nascimento."""
    if not data_nascimento:
        return None
    hoje = hoje or date.today()
    if isinstance(data_nascimento, str):
        data_nascimento = date.fromisoformat(data_nascimento)
    return hoje.year - data_nascimento.year - ((hoje.month, hoje.day) < (data_nascimento.month, data_nascimento.day))


def classificar_risco(percentual_risco):
    """Classifica o percentual de risco em baixo, intermediario ou alto."""
    if percentual_risco < 10:
        return "baixo"
    if percentual_risco < 20:
        return "intermediario"
    return "alto"


def recomendacoes_por_risco(classe_risco, fumante=False, diabetes=False, pressao_sistolica=None, hdl=None):
    """Gera recomendacoes basicas conforme risco e fatores clinicos."""
    recomendacoes = [
        "Mantenha acompanhamento cardiologico regular.",
        "Priorize atividade fisica, sono adequado e alimentacao com baixo teor de ultraprocessados.",
    ]
    if classe_risco == "alto":
        recomendacoes.insert(0, "Procure avaliacao medica para plano intensivo de reducao de risco.")
    elif classe_risco == "intermediario":
        recomendacoes.insert(0, "Discuta metas de pressao, colesterol e glicemia com seu cardiologista.")
    if fumante:
        recomendacoes.append("Interromper tabagismo e a medida isolada de maior impacto no seu perfil.")
    if diabetes:
        recomendacoes.append("Controle glicemico deve ser acompanhado junto com a estrategia cardiovascular.")
    if pressao_sistolica and pressao_sistolica >= 140:
        recomendacoes.append("Pressao sistolica elevada: monitore em casa e leve os registros a consulta.")
    if hdl and hdl < 40:
        recomendacoes.append("HDL baixo: atividade aerobica e ajuste alimentar podem ajudar no perfil lipidico.")
    return recomendacoes


def calcular_risco_framingham(
    *,
    sexo,
    idade,
    colesterol_total,
    hdl,
    pressao_sistolica,
    trata_pressao=False,
    fumante=False,
    diabetes=False,
):
    """Calcula risco cardiovascular em 10 anos pelo escore de Framingham."""
    sexo = (sexo or "").upper()[0:1]
    if sexo not in COEFICIENTES_FRAMINGHAM:
        raise ValueError("sexo deve ser M ou F")

    valores = {
        "idade": idade,
        "colesterol total": colesterol_total,
        "HDL": hdl,
        "pressao sistolica": pressao_sistolica,
    }
    for rotulo, valor in valores.items():
        if valor is None or float(valor) <= 0:
            raise ValueError(f"{rotulo} deve ser maior que zero")

    if not 30 <= int(idade) <= 74:
        raise ValueError("idade deve estar entre 30 e 74 anos para o escore de Framingham")

    coeficiente = COEFICIENTES_FRAMINGHAM[sexo]
    chave_pressao = "ln_pressao_tratada" if trata_pressao else "ln_pressao_nao_tratada"
    pontuacao = (
        math.log(idade) * coeficiente["ln_idade"]
        + math.log(colesterol_total) * coeficiente["ln_colesterol_total"]
        + math.log(hdl) * coeficiente["ln_hdl"]
        + math.log(pressao_sistolica) * coeficiente[chave_pressao]
        + (coeficiente["fumante"] if fumante else 0)
        + (coeficiente["diabetes"] if diabetes else 0)
    )
    risco = 1 - coeficiente["sobrevida_base"] ** math.exp(pontuacao - coeficiente["media"])
    percentual_risco = round(max(0, min(risco * 100, 100)), 1)
    classe_risco = classificar_risco(percentual_risco)
    return {
        "risco_percentual": percentual_risco,
        "classe_risco": classe_risco,
        "media_populacional_percentual": estimar_media_populacional(sexo, idade),
        "recomendacoes": recomendacoes_por_risco(classe_risco, fumante, diabetes, pressao_sistolica, hdl),
    }


def estimar_media_populacional(sexo, idade):
    """Estima a referência populacional usada para contextualizar o risco individual."""
    base = 4 if sexo == "F" else 6
    fator_idade = max(0, idade - 30) * (0.28 if sexo == "F" else 0.34)
    return round(min(base + fator_idade, 35), 1)

