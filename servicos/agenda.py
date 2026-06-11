from datetime import date, datetime, time, timedelta
from urllib.parse import quote

from servicos.formatacao import formatar_data_br, formatar_horario


STATUS_CONSULTA_ATIVA = ("agendada", "confirmada", "em_atendimento")


def normalizar_horario(valor):
    """Converte horário vindo do formulário, banco ou timedelta."""
    if isinstance(valor, time):
        return valor
    if isinstance(valor, timedelta):
        segundos = int(valor.total_seconds())
        return time(segundos // 3600, (segundos % 3600) // 60, segundos % 60)
    if isinstance(valor, str):
        return datetime.strptime(valor[:5], "%H:%M").time()
    raise ValueError("horário inválido")


def juntar_data_e_horario(data_consulta, horario_consulta):
    """Une data e horário de uma consulta em um datetime comparável."""
    if isinstance(data_consulta, datetime):
        data_base = data_consulta.date()
    elif isinstance(data_consulta, date):
        data_base = data_consulta
    else:
        data_base = date.fromisoformat(str(data_consulta))
    return datetime.combine(data_base, normalizar_horario(horario_consulta))


def consulta_no_futuro(data_consulta, horario_consulta, agora=None):
    """Informa se a consulta escolhida ainda não passou."""
    referencia = agora or datetime.now()
    return juntar_data_e_horario(data_consulta, horario_consulta) > referencia


def bloquear_horarios_passados(horarios, data_escolhida, agora=None):
    """Marca como indisponíveis os horários de hoje que já passaram."""
    referencia = agora or datetime.now()
    if isinstance(data_escolhida, str):
        data_escolhida = date.fromisoformat(data_escolhida)
    if data_escolhida != referencia.date():
        return horarios

    ajustados = []
    for horario in horarios:
        ainda_vai_acontecer = juntar_data_e_horario(data_escolhida, horario["horario"]) > referencia
        ajustados.append(
            {
                **horario,
                "disponivel": bool(horario.get("disponivel")) and ainda_vai_acontecer,
                "situacao": horario.get("situacao") if ainda_vai_acontecer else "passado",
            }
        )
    return ajustados


def converter_horario_para_minutos(valor):
    """Transforma um horário em minutos desde meia-noite."""
    horario = normalizar_horario(valor)
    return horario.hour * 60 + horario.minute


def horarios_se_sobrepoem(inicio_a, duracao_a, inicio_b, duracao_b):
    """Verifica se dois intervalos de atendimento ocupam o mesmo período."""
    a_inicio = converter_horario_para_minutos(inicio_a)
    b_inicio = converter_horario_para_minutos(inicio_b)
    a_fim = a_inicio + int(duracao_a or 30)
    b_fim = b_inicio + int(duracao_b or 30)
    return a_inicio < b_fim and b_inicio < a_fim


def encontrar_conflito_de_agenda(consultas_existentes, horario_inicio, duracao_minutos):
    """Retorna a consulta que conflita com o novo horário, se existir."""
    for consulta in consultas_existentes:
        if horarios_se_sobrepoem(
            horario_inicio,
            duracao_minutos,
            consulta["horario_consulta"],
            consulta.get("duracao_minutos") or 30,
        ):
            return consulta
    return None


def horario_dentro_do_expediente(horario_inicio, duracao_minutos, inicio_expediente, fim_expediente):
    """Confirma se um atendimento cabe dentro do expediente do médico."""
    inicio = converter_horario_para_minutos(horario_inicio)
    fim = inicio + int(duracao_minutos or 30)
    return inicio >= converter_horario_para_minutos(inicio_expediente) and fim <= converter_horario_para_minutos(fim_expediente)


def montar_horarios_disponiveis(inicio_expediente, fim_expediente, duracao_minutos, consultas_ocupadas, passo_minutos=30):
    """Cria a lista de horários livres e ocupados para a agenda."""
    horarios = []
    atual = converter_horario_para_minutos(inicio_expediente)
    fim = converter_horario_para_minutos(fim_expediente)
    while atual + int(duracao_minutos or 30) <= fim:
        horario_atual = time(atual // 60, atual % 60)
        conflito = encontrar_conflito_de_agenda(consultas_ocupadas, horario_atual, duracao_minutos)
        horarios.append(
            {
                "horario": horario_atual.strftime("%H:%M"),
                "disponivel": conflito is None,
                "situacao": "disponivel" if conflito is None else "ocupado",
            }
        )
        atual += passo_minutos
    return horarios


def montar_link_whatsapp_confirmacao(numero, consulta, nome_servico="", nome_medico=""):
    """Gera o link de WhatsApp com mensagem pronta para confirmar consulta."""
    data_texto = formatar_data_br(consulta["data_consulta"])
    horario = formatar_horario(normalizar_horario(consulta["horario_consulta"]))
    mensagem = (
        "Olá! Quero confirmar minha consulta na CardioLab. "
        f"Serviço: {nome_servico or 'consulta'}, médico(a): {nome_medico or 'CardioLab'}, "
        f"data: {data_texto}, horário: {horario}. "
        "Estou ciente das instruções de preparo."
    )
    return f"https://wa.me/{numero}?text={quote(mensagem)}"

