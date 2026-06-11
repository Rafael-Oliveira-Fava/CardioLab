import logging
from datetime import datetime, timedelta


logger = logging.getLogger(__name__)


JANELAS_LEMBRETE = (
    ("24h", timedelta(hours=24), timedelta(minutes=20)),
    ("2h", timedelta(hours=2), timedelta(minutes=20)),
)


def registrar_lembretes_consulta(app):
    """Procura consultas próximas e cria lembretes internos para o paciente."""

    with app.app_context():
        db = app.obter_banco()
        cursor = db.cursor()
        agora = datetime.now()

        for tipo_lembrete, antecedencia, tolerancia in JANELAS_LEMBRETE:
            inicio = agora + antecedencia - tolerancia
            fim = agora + antecedencia + tolerancia
            cursor.execute(
                """
                SELECT a.*, s.nome as nome_servico
                FROM consultas a
                JOIN servicos s ON a.servico_id = s.id
                LEFT JOIN lembretes_consulta ar
                  ON ar.consulta_id = a.id AND ar.tipo_lembrete = %s
                WHERE a.situacao IN ('agendada', 'confirmada')
                  AND TIMESTAMP(a.data_consulta, a.horario_consulta) BETWEEN %s AND %s
                  AND ar.id IS NULL
                """,
                (tipo_lembrete, inicio, fim),
            )
            consultas = cursor.fetchall()
            for consulta in consultas:
                try:
                    cursor.execute(
                        """
                        INSERT INTO lembretes_consulta (consulta_id, tipo_lembrete, enviado_em)
                        VALUES (%s, %s, NOW())
                        """,
                        (consulta["id"], tipo_lembrete),
                    )
                    cursor.execute(
                        """
                        INSERT INTO notificacoes (usuario_id, titulo, mensagem, tipo)
                        SELECT p.usuario_id, 'Lembrete de consulta', %s, 'lembrete'
                        FROM pacientes p WHERE p.id = %s
                        """,
                        (
                            f"Sua consulta de {consulta['nome_servico']} será em aproximadamente {tipo_lembrete}.",
                            consulta["paciente_id"],
                        ),
                    )
                    db.commit()
                except Exception:
                    db.rollback()
                    logger.exception(
                        "erro_lembrete_consulta",
                        extra={"extra": {"consulta_id": consulta["id"], "tipo_lembrete": tipo_lembrete}},
                    )
        cursor.close()


