import re
import unicodedata

from extensoes import obter_banco


ESTATISTICAS_HOME = {"pacientes": 2500, "exames": 15000, "anos": 15, "satisfacao": 98}

PERGUNTAS_FREQUENTES = [
    {
        "question": "Como marcar uma consulta?",
        "answer": "Você pode agendar pelo portal, WhatsApp ou central de atendimento.",
    },
    {
        "question": "Como acessar meus exames?",
        "answer": "Acesse o portal do paciente e abra a área de resultados.",
    },
    {
        "question": "Como funciona a teleconsulta?",
        "answer": "Ao confirmar uma teleconsulta, o sistema gera uma sala Jitsi exclusiva.",
    },
]


FOTOS_PUBLICAS_MEDICOS = {
    "dr.ricardo@cardiolab.com.br": "assets/medicos/ricardo-souza.jpg",
    "dra.helena@cardiolab.com.br": "assets/medicos/helena-costa.jpg",
    "dr.bruno@cardiolab.com.br": "assets/medicos/bruno-almeida.jpg",
    "dra.camila@cardiolab.com.br": "assets/medicos/camila-torres.jpg",
}


def criar_slug(valor):
    """Transforma titulo de artigo em texto seguro para URL."""
    normalizado = unicodedata.normalize("NFKD", valor or "")
    texto_ascii = normalizado.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", texto_ascii.lower()).strip("-")
    return slug or "artigo"


def buscar_todos(consulta, parametros=()):
    """Executa consulta SQL e retorna todas as linhas."""
    banco = obter_banco()
    cursor = banco.cursor()
    try:
        cursor.execute(consulta, parametros)
        return cursor.fetchall()
    finally:
        cursor.close()


def buscar_um(consulta, parametros=()):
    """Executa consulta SQL e retorna apenas a primeira linha."""
    banco = obter_banco()
    cursor = banco.cursor()
    try:
        cursor.execute(consulta, parametros)
        return cursor.fetchone()
    finally:
        cursor.close()


def conteudo_da_pagina_inicial():
    """Carrega serviços, avaliações, artigos e números da página inicial."""
    return {
        "servicos": listar_servicos(limite=8),
        "avaliacoes": buscar_todos("SELECT * FROM avaliacoes ORDER BY criado_em DESC LIMIT 6"),
        "artigos": listar_artigos(3),
        "estatisticas": ESTATISTICAS_HOME,
    }


def listar_servicos(limite=None):
    """Lista serviços exibidos nas páginas públicas e no agendamento."""
    trecho_limite = " LIMIT %s" if limite else ""
    parametros = (limite,) if limite else ()
    return buscar_todos(
        f"""
        SELECT id, nome, descricao, preparo, duracao_minutos, indicacao
        FROM servicos
        ORDER BY id{trecho_limite}
        """,
        parametros,
    )


def listar_medicos():
    """Lista médicos ativos já com fotos públicas resolvidas."""
    medicos = buscar_todos(
        """
        SELECT d.*, u.nome, u.email, u.foto_perfil
        FROM medicos d
        JOIN usuarios u ON d.usuario_id = u.id
        WHERE u.ativo = 1
        ORDER BY u.nome
        """
    )
    return completar_fotos_medicos(medicos)


def completar_fotos_medicos(medicos):
    """Substitui avatares genéricos por fotos reais quando disponíveis."""
    for medico in medicos or []:
        foto = medico.get("foto_perfil") or ""
        avatar_generico = not foto or "/assets/avatars/medico-" in foto or foto.endswith(".svg")
        medico["arquivo_foto_publica"] = FOTOS_PUBLICAS_MEDICOS.get(medico.get("email", "").lower()) if avatar_generico else None
    return medicos


def listar_artigos(limite=None):
    """Lista artigos educativos e adiciona slug para link amigável."""
    trecho_limite = " LIMIT %s" if limite else ""
    parametros = (limite,) if limite else ()
    artigos = buscar_todos(
        f"""
        SELECT id, titulo, categoria, conteudo, imagem_url, criado_em
        FROM artigos
        ORDER BY criado_em DESC{trecho_limite}
        """,
        parametros,
    )
    for artigo in artigos:
        artigo["slug"] = criar_slug(artigo.get("titulo"))
    return artigos


def buscar_artigo(artigo_id):
    """Busca um artigo específico pelo identificador."""
    artigo = buscar_um(
        """
        SELECT id, titulo, categoria, conteudo, imagem_url, criado_em
        FROM artigos
        WHERE id = %s
        LIMIT 1
        """,
        (artigo_id,),
    )
    if artigo:
        artigo["slug"] = criar_slug(artigo.get("titulo"))
    return artigo


def listar_artigos_relacionados(artigo_id, limite=3):
    """Busca artigos recentes diferentes do artigo atual."""
    artigos = buscar_todos(
        """
        SELECT id, titulo, categoria, conteudo, imagem_url, criado_em
        FROM artigos
        WHERE id <> %s
        ORDER BY criado_em DESC
        LIMIT %s
        """,
        (artigo_id, limite),
    )
    for artigo in artigos:
        artigo["slug"] = criar_slug(artigo.get("titulo"))
    return artigos


def buscar_exame_compartilhado(token):
    """Busca exame acessado por link público temporário."""
    return buscar_um(
        """
        SELECT e.*, e.titulo, est.expira_em
        FROM tokens_compartilhamento_exames est
        JOIN resultados_exames e ON est.exame_id = e.id
        WHERE est.token = %s AND est.expira_em > NOW()
        LIMIT 1
        """,
        (token,),
    )



