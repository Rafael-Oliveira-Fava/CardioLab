"""Formatação PT-BR para datas, horários e textos curtos."""

from datetime import date, datetime, time, timedelta


MESES_ABREVIADOS = (
    "jan",
    "fev",
    "mar",
    "abr",
    "mai",
    "jun",
    "jul",
    "ago",
    "set",
    "out",
    "nov",
    "dez",
)

DIAS_SEMANA_CURTOS = ("seg", "ter", "qua", "qui", "sex", "sáb", "dom")


def normalizar_data(valor):
    """Converte strings e datetimes para date."""
    if not valor:
        return None
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    return date.fromisoformat(str(valor)[:10])


def normalizar_horario(valor):
    """Converte strings e timedeltas para time."""
    if not valor:
        return None
    if isinstance(valor, time):
        return valor
    if isinstance(valor, timedelta):
        segundos = int(valor.total_seconds())
        return time(segundos // 3600, (segundos % 3600) // 60, segundos % 60)
    return datetime.strptime(str(valor)[:5], "%H:%M").time()


def formatar_data_br(valor):
    """Formata uma data completa no padrão brasileiro dd/mm/aaaa."""
    data = normalizar_data(valor)
    return data.strftime("%d/%m/%Y") if data else "-"


def formatar_data_curta(valor):
    """Formata uma data curta no padrão brasileiro dd/mm."""
    data = normalizar_data(valor)
    return data.strftime("%d/%m") if data else "-"


def formatar_horario(valor):
    """Formata um horário no padrão 24 horas HH:MM."""
    horario = normalizar_horario(valor)
    return horario.strftime("%H:%M") if horario else "-"


def formatar_data_hora_curta(valor):
    """Formata data e horário para listas compactas de notificações."""
    if not valor:
        return "-"
    if isinstance(valor, datetime):
        data_hora = valor
    else:
        data_hora = datetime.fromisoformat(str(valor).replace(" ", "T"))
    return f"{formatar_data_curta(data_hora.date())} {formatar_horario(data_hora.time())}"


def mes_abreviado(valor):
    """Retorna o mês abreviado em português para cartões de consulta."""
    data = normalizar_data(valor)
    return MESES_ABREVIADOS[data.month - 1] if data else ""


def dia_do_mes(valor):
    """Retorna apenas o dia do mês com dois dígitos."""
    data = normalizar_data(valor)
    return f"{data.day:02d}" if data else ""


def dia_semana_curto(valor):
    """Retorna o dia da semana abreviado em português."""
    data = normalizar_data(valor)
    return DIAS_SEMANA_CURTOS[data.weekday()] if data else ""

