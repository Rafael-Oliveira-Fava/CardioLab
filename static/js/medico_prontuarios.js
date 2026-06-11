/**
 * Inicializa interações do painel médico: fila de atendimento e prontuário lateral.
 */
document.addEventListener('DOMContentLoaded', () => {
    iniciarFilaMedico();

    document.querySelectorAll('[data-painel-prontuario-close]').forEach((botao) => {
        botao.addEventListener('click', fecharPainelProntuario);
    });

    document.querySelectorAll('[data-paciente]').forEach((item) => {
        item.addEventListener('click', (evento) => {
            if (evento.target.closest('form, a, button')) return;
            abrirPainelProntuario(item.dataset.paciente);
        });
    });
});

/**
 * Permite reordenar consultas por arrastar e soltar dentro da fila do médico.
 */
function iniciarFilaMedico() {
    const fila = document.getElementById('fila-medico');
    if (!fila) return;

    let itemArrastado = null;

    fila.querySelectorAll('.item-fila').forEach((item) => {
        item.addEventListener('dragstart', () => {
            itemArrastado = item;
            item.classList.add('arrastando');
        });

        item.addEventListener('dragend', () => {
            item.classList.remove('arrastando');
            itemArrastado = null;
            salvarOrdemFila(fila);
        });

        item.addEventListener('dragover', (evento) => {
            evento.preventDefault();
            if (!itemArrastado || itemArrastado === item) return;
            const inserirDepois = evento.offsetY > item.offsetHeight / 2;
            fila.insertBefore(itemArrastado, inserirDepois ?item.nextSibling : item);
        });
    });
}

/**
 * Envia a nova ordem das consultas para persistência no backend.
 */
async function salvarOrdemFila(fila) {
    const idsConsultas = [...fila.querySelectorAll('.item-fila')].map((item) => item.dataset.id);

    await fetch('/medico/fila/reordenar', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ids_consultas: idsConsultas })
    });
}

/**
 * Abre o painel lateral e carrega dados clínicos do paciente selecionado.
 */
async function abrirPainelProntuario(pacienteId) {
    if (!pacienteId) return;

    const painel = document.getElementById('painel-deslizante-prontuario');
    const conteudo = document.getElementById('painel-prontuario-conteudo');
    if (!painel || !conteudo) return;

    painel.classList.remove('hidden');
    conteudo.innerHTML = '<p class="text-gray-500">Carregando prontuário...</p>';

    const dados = await carregarProntuarioPaciente(pacienteId);
    if (!dados || dados.erro) {
        conteudo.innerHTML = '<p class="text-red-600">Não foi possível carregar o prontuário.</p>';
        return;
    }

    const prontuarios = (dados.prontuarios_paciente || []).map((prontuario) => `
        <div class="bloco-prontuario">
            <p>${escaparHtml(prontuario.criado_em || '')}</p>
            <span>${escaparHtml(prontuario.observacoes || 'Sem observações.')}</span>
        </div>
    `).join('');

    const indiceAvatar = (((Number(pacienteId) || 1) - 1) % 6) + 1;
    const fotoPaciente = escaparHtml(dados.paciente.foto_perfil || `/static/assets/avatars/paciente-${indiceAvatar}.svg`);
    const nomePaciente = escaparHtml(dados.paciente.nome || '');
    const carteirinha = montarCarteirinhaInline(dados.paciente);

    conteudo.innerHTML = `
        <p class="chamada-cartao">Prontuário</p>
        <div class="flex items-center gap-4">
            <img class="foto-cabecalho-medico" src="${fotoPaciente}" alt="Foto de ${nomePaciente}">
            <div>
                <h2 class="font-display text-3xl text-dark">${nomePaciente}</h2>
                <p class="text-sm text-gray-500">${escaparHtml(dados.paciente.email || '')}</p>
            </div>
        </div>
        ${carteirinha}
        <div class="alerta-risco medio">CPF: ${escaparHtml(dados.paciente.cpf || '-')}</div>
        <h3 class="font-black text-dark">Histórico</h3>
        ${prontuarios || '<p class="text-gray-400">Sem registros.</p>'}
    `;
}

/**
 * Monta um resumo da carteirinha CardioLab Care dentro do prontuário.
 */
function montarCarteirinhaInline(paciente) {
    if (!paciente.nome_plano_carteirinha) {
        return '<div class="carteirinha-inline suave"><span>Sem carteirinha CardioLab Care</span><strong>Particular</strong></div>';
    }

    const situacao = paciente.situacao_carteirinha === 'ativa'
        ?'CardioLab Care ativo'
        : 'CardioLab Care em análise';

    return `
        <div class="carteirinha-inline">
            <span>${situacao}</span>
            <strong>${escaparHtml(paciente.nome_plano_carteirinha)}</strong>
            <small>${escaparHtml(paciente.numero_carteirinha || '-')}</small>
        </div>
    `;
}

/**
 * Busca prontuário, exames, métricas e dados cadastrais pela API médica.
 */
async function carregarProntuarioPaciente(pacienteId) {
    try {
        const resposta = await fetch(`/medico/api/pacientes/${encodeURIComponent(pacienteId)}`);
        if (!resposta.ok) return null;
        return resposta.json();
    } catch (erro) {
        return null;
    }
}

/**
 * Fecha o painel lateral sem descartar os dados já carregados no DOM.
 */
function fecharPainelProntuario() {
    const painel = document.getElementById('painel-deslizante-prontuario');
    if (painel) painel.classList.add('hidden');
}

/**
 * Escapa conteúdo dinâmico antes de inseri-lo em templates HTML.
 */
function escaparHtml(valor) {
    const elemento = document.createElement('div');
    elemento.textContent = valor == null ? '' : String(valor);
    return elemento.innerHTML;
}
