"""
CardioLab - rotas públicas.
"""

from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for

from servicos.conteudo_publico import (
    PERGUNTAS_FREQUENTES,
    buscar_artigo,
    buscar_exame_compartilhado,
    conteudo_da_pagina_inicial,
    listar_artigos,
    listar_artigos_relacionados,
    listar_medicos,
    listar_servicos,
)


rotas_publicas = Blueprint("publico", __name__)


@rotas_publicas.route("/")
def inicio():
    """Renderiza a página inicial com chamadas, serviços, médicos, depoimentos e artigos."""

    return render_template(
        "inicio.html",
        descricao_pagina="CardioLab oferece cardiologia premium, exames avançados, agendamento digital e portal seguro para pacientes.",
        **conteudo_da_pagina_inicial(),
    )


@rotas_publicas.route("/servicos")
def servicos():
    """Lista serviços cardiológicos públicos com preparo e descrição."""

    return render_template(
        "servicos.html",
        servicos=listar_servicos(),
        descricao_pagina="Conheça os exames e consultas cardiológicas da CardioLab, com preparo orientado e acompanhamento digital.",
    )


@rotas_publicas.route("/equipe")
def equipe():
    """Mostra a equipe médica pública com fotos, especialidades e currículos."""

    return render_template(
        "equipe_medica.html",
        medicos=listar_medicos(),
        descricao_pagina="Conheça a equipe médica da CardioLab, especialistas em cardiologia, prevenção, arritmias e ecocardiografia.",
    )


@rotas_publicas.route("/artigos")
def artigos():
    """Exibe a lista de artigos educativos publicados pela clínica."""

    return render_template(
        "artigos.html",
        artigos=listar_artigos(),
        descricao_pagina="Artigos de cardiologia, prevenção cardiovascular, exames, pressão alta e colesterol pela equipe CardioLab.",
    )


@rotas_publicas.route("/blog")
def blog():
    """Mantém o endereço blog funcionando e envia para os artigos."""

    return redirect(url_for("publico.artigos"), code=301)


@rotas_publicas.route("/artigos/<int:artigo_id>")
@rotas_publicas.route("/artigos/<int:artigo_id>/")
@rotas_publicas.route("/artigos/<int:artigo_id>/<slug>")
def artigo(artigo_id, slug=None):
    """Carrega um artigo público e aplica URL canônica baseada no slug."""

    artigo_encontrado = buscar_artigo(artigo_id)
    if not artigo_encontrado:
        abort(404)
    if slug != artigo_encontrado["slug"]:
        return redirect(url_for("publico.artigo", artigo_id=artigo_id, slug=artigo_encontrado["slug"]), code=301)
    resumo = artigo_encontrado["conteudo"].split("\n\n", 1)[0].replace("**", "")
    return render_template(
        "artigo.html",
        artigo=artigo_encontrado,
        artigos_relacionados=listar_artigos_relacionados(artigo_id),
        tipo_pagina="article",
        descricao_pagina=resumo[:160],
    )


@rotas_publicas.route("/agendar")
def agendar():
    """Guarda intenção de agendamento e envia o usuário para o fluxo correto."""

    intencao = {
        key: value
        for key, value in {
            "servico_id": request.args.get("servico_id"),
            "medico_id": request.args.get("medico_id"),
        }.items()
        if value
    }
    session["intencao_agendamento"] = intencao

    argumentos_painel = {"agendar": "1", **intencao}
    endereco_painel = url_for("paciente.painel", **argumentos_painel)
    usuario = session.get("usuario")
    if usuario:
        if usuario.get("perfil") == "paciente":
            return redirect(endereco_painel)
        if usuario.get("perfil") == "administrador":
            return redirect(url_for("administracao.painel"))
        flash("Agendamentos de pacientes ficam no portal do paciente.", "informacao")
        return redirect(url_for("medico.painel"))

    flash("Entre ou crie sua conta para concluir o agendamento que você iniciou.", "informacao")
    return redirect(url_for("autenticacao.entrar", proximo=endereco_painel))


@rotas_publicas.route("/duvidas")
def duvidas():
    """Renderiza perguntas frequentes sobre atendimento, exames e portal."""

    return render_template("duvidas.html", faqs=PERGUNTAS_FREQUENTES, descricao_pagina="Perguntas frequentes sobre consultas, exames, teleconsulta e portal do paciente CardioLab.")


@rotas_publicas.route("/lgpd")
@rotas_publicas.route("/privacidade")
def lgpd():
    """Abre a página legal diretamente na aba de privacidade e LGPD."""

    return render_template("privacidade_lgpd.html", aba_ativa="privacidade", descricao_pagina="Política de privacidade, LGPD, termos de uso e tratamento de dados na CardioLab.")


@rotas_publicas.route("/termos-de-uso")
def termos():
    """Abre a página legal diretamente na aba de termos de uso."""

    return render_template("privacidade_lgpd.html", aba_ativa="termos", descricao_pagina="Termos de uso do portal e serviços digitais da CardioLab.")


@rotas_publicas.route("/cookies")
def cookies():
    """Abre a página legal diretamente na aba de política de cookies."""

    return render_template("privacidade_lgpd.html", aba_ativa="cookies", descricao_pagina="Política de cookies e preferências de navegação da CardioLab.")


@rotas_publicas.route("/compartilhar/exames/<token>")
def exame_compartilhado(token):
    """Mostra exame compartilhado apenas quando o token público é válido."""

    exame = buscar_exame_compartilhado(token)
    if not exame:
        abort(404)
    return render_template("exame_compartilhado.html", exame=exame)



