"""Regras de exames do paciente e visualização segura de resultados."""

import io
from datetime import datetime
from pathlib import Path
from uuid import uuid4


TIPOS_VISUALIZAVEIS = {"pdf", "imagem"}


def listar_exames_paciente(cursor, paciente_id, limite=10):
    """Lista os últimos exames do paciente com serviço e médico responsáveis."""

    cursor.execute(
        """
        SELECT e.*, e.titulo, s.nome as nome_servico, u.nome as nome_medico
        FROM resultados_exames e
        LEFT JOIN servicos s ON e.servico_id = s.id
        LEFT JOIN medicos d ON e.medico_id = d.id
        LEFT JOIN usuarios u ON d.usuario_id = u.id
        WHERE e.paciente_id = %s
        ORDER BY e.criado_em DESC
        LIMIT %s
        """,
        (paciente_id, limite),
    )
    return cursor.fetchall()


def buscar_exame_paciente(cursor, exame_id, paciente_id):
    """Busca um exame garantindo que ele pertence ao paciente informado."""

    cursor.execute(
        """
        SELECT e.*, e.titulo, s.nome as nome_servico, du.nome as nome_medico,
               pu.nome as nome_paciente, pu.cpf as cpf_paciente
        FROM resultados_exames e
        JOIN pacientes p ON e.paciente_id = p.id
        JOIN usuarios pu ON p.usuario_id = pu.id
        LEFT JOIN servicos s ON e.servico_id = s.id
        LEFT JOIN medicos d ON e.medico_id = d.id
        LEFT JOIN usuarios du ON d.usuario_id = du.id
        WHERE e.id = %s AND e.paciente_id = %s
        LIMIT 1
        """,
        (exame_id, paciente_id),
    )
    return cursor.fetchone()


def criar_token_compartilhamento(cursor, exame_id, token=None):
    """Cria token temporário de 48 horas para compartilhar um exame."""

    token = token or uuid4().hex
    cursor.execute(
        """
        INSERT INTO tokens_compartilhamento_exames (exame_id, token, expira_em)
        VALUES (%s, %s, DATE_ADD(NOW(), INTERVAL 48 HOUR))
        """,
        (exame_id, token),
    )
    return token


def resolver_caminho_arquivo_exame(caminho_raiz, arquivo_url):
    """Resolve arquivo_url dentro da pasta do app e bloqueia caminhos inseguros."""

    if not arquivo_url:
        return None

    url_limpa = str(arquivo_url).split("?", 1)[0].replace("\\", "/").strip()
    if url_limpa.startswith(("http://", "https://", "//")):
        return None

    raiz = Path(caminho_raiz).resolve()
    raiz_arquivos_enviados = (raiz / "static" / "arquivos_enviados").resolve()
    candidato = (raiz / url_limpa.lstrip("/")).resolve()
    try:
        candidato.relative_to(raiz_arquivos_enviados)
    except ValueError:
        return None
    return candidato


def montar_visualizacao_exame(exame, arquivo_disponivel=False):
    """Define se a página mostra arquivo real ou simulação de manutenção."""

    tipo_resultado = (exame or {}).get("tipo_resultado") or "pdf"
    arquivo_url = (exame or {}).get("arquivo_url")
    pode_exibir_arquivo = bool(arquivo_disponivel and arquivo_url and tipo_resultado in TIPOS_VISUALIZAVEIS)
    if pode_exibir_arquivo:
        return {
            "situacao": "disponivel",
            "modo": tipo_resultado,
            "titulo": "Pré-visualização disponível",
            "mensagem": "O arquivo do exame foi encontrado e pode ser visualizado nesta página.",
        }
    return {
        "situacao": "manutencao",
        "modo": "simulacao",
        "titulo": "Visualização em manutenção",
        "mensagem": "A área de visualização está em fase de implantação. Os dados abaixo simulam a tela final do laudo.",
    }


def gerar_pdf_com_marca_dagua(caminho_origem, nome_paciente, cpf_paciente, gerado_em=None):
    """Aplica marca d'água em um PDF e devolve o arquivo em memória."""

    from pypdf import PdfReader, PdfWriter
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    gerado_em = gerado_em or datetime.now()
    memoria_marca_dagua = io.BytesIO()
    pdf = canvas.Canvas(memoria_marca_dagua, pagesize=A4)
    pdf.setFont("Helvetica", 10)
    pdf.setFillAlpha(0.16)
    pdf.rotate(35)
    pdf.drawString(180, 90, f"CardioLab - {nome_paciente} - CPF {cpf_paciente} - {gerado_em:%d/%m/%Y}")
    pdf.save()
    memoria_marca_dagua.seek(0)
    pagina_marca_dagua = PdfReader(memoria_marca_dagua).pages[0]

    leitor_pdf = PdfReader(str(caminho_origem))
    escritor_pdf = PdfWriter()
    for pagina in leitor_pdf.pages:
        pagina.merge_page(pagina_marca_dagua)
        escritor_pdf.add_page(pagina)

    saida = io.BytesIO()
    escritor_pdf.write(saida)
    saida.seek(0)
    return saida


def nome_download_exame(exame_id):
    """Padroniza o nome do arquivo baixado pelo paciente."""

    return f"cardiolab-exame-{int(exame_id)}.pdf"

