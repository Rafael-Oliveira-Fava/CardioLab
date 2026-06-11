/**
 * Inicializa recursos interativos do portal do paciente após o carregamento da página.
 */
document.addEventListener('DOMContentLoaded', function() {
    const hoje = obterDataIsoDeHoje();
    document.querySelectorAll('input[name="data_consulta"]').forEach((campo) => {
        campo.setAttribute('min', hoje);
    });

    document.querySelectorAll('form[action*="cancelar"]').forEach((formulario) => {
        formulario.addEventListener('submit', function(evento) {
            if (!confirm('Tem certeza que deseja cancelar esta consulta? Cancelamentos precisam respeitar a antecedência mínima.')) {
                evento.preventDefault();
            }
        });
    });

    iniciarPlanejadorConsulta();
    iniciarContagens();
    iniciarGraficosMiniatura();
    iniciarFormulariosRemarcacao();
    iniciarNotificacoesPaciente();
    iniciarControlesJanelaConsulta();
});

/**
 * Controla o fluxo de escolha de médico, serviço, dia e horário para agendamento.
 */
function iniciarPlanejadorConsulta() {
    const campoMedico = document.getElementById('consulta-medico');
    const campoServico = document.getElementById('consulta-servico');
    const campoData = document.getElementById('data-consulta');
    const campoHorario = document.getElementById('consulta-horario');
    const gradeHorarios = document.getElementById('calendario-horarios');
    const gradeCalendario = document.getElementById('grade-calendario-consulta');
    const cartoesMedico = document.querySelectorAll('.cartao-escolha-medico');
    const perfilMedico = document.getElementById('perfil-medico-selecionado');
    const rotuloData = document.getElementById('rotulo-data-selecionada');
    const rotuloHorario = document.getElementById('rotulo-horario-selecionado');
    const sugestao = document.getElementById('sugestao-medico');

    if (!campoMedico || !campoServico || !campoData || !campoHorario || !gradeHorarios) return;

    cartoesMedico.forEach((cartao) => {
        cartao.addEventListener('click', () => {
            cartoesMedico.forEach((item) => item.classList.remove('selecionado'));
            cartao.classList.add('selecionado');
            campoMedico.value = cartao.dataset.medicoId;

            if (perfilMedico) {
                const foto = cartao.dataset.fotoMedico || cartao.querySelector('.foto-medico')?.getAttribute('src') || '';
                perfilMedico.innerHTML = `
                    ${foto ?`<img class="foto-medico foto-medico-selecionado" src="${escaparHtml(foto)}" alt="Foto de ${escaparHtml(cartao.dataset.medicoNome)}">` : ''}
                    <p class="chamada-cartao">Perfil médico</p>
                    <h3>${escaparHtml(cartao.dataset.medicoNome)}</h3>
                    <strong>${escaparHtml(cartao.dataset.medicoEspecialidade)} · ${escaparHtml(cartao.dataset.medicoCrm)}</strong>
                    <p>${escaparHtml(cartao.dataset.medicoBiografia)}</p>
                `;
            }

            carregarCalendario();
            carregarHorarios();
        });
    });

    campoServico.addEventListener('change', async () => {
        if (!campoServico.value || !sugestao) return;
        if (campoMedico.value) {
            sugestao.classList.add('hidden');
            carregarCalendario();
            carregarHorarios();
            return;
        }

        try {
            const resposta = await fetch(`/paciente/api/sugerir-medico?servico_id=${campoServico.value}`);
            const dados = await resposta.json();
            if (dados.medico) {
                sugestao.textContent = `Sugestão: ${dados.medico.nome} tem ${dados.medico.vagas_livres} horários livres nos próximos 7 dias.`;
                sugestao.classList.remove('hidden');
                campoMedico.value = dados.medico.id;
                const cartao = document.querySelector(`.cartao-escolha-medico[data-medico-id="${dados.medico.id}"]`);
                if (cartao) cartao.click();
            }
        } catch (erro) {
            sugestao.classList.add('hidden');
        }
    });

    [campoMedico, campoServico].forEach((campo) => {
        campo.addEventListener('change', () => {
            carregarCalendario();
            carregarHorarios();
        });
    });

    campoData.addEventListener('change', () => {
        if (rotuloData) rotuloData.textContent = formatarDataCurta(campoData.value);
        carregarHorarios();
    });

    aplicarIntencaoDeAgendamento();

    /**
     * Consulta a API e renderiza os próximos dias disponíveis para médico e serviço.
     */
    async function carregarCalendario() {
        if (!campoMedico.value || !campoServico.value || !gradeCalendario) return;
        mostrarMensagemCalendario(gradeCalendario, 'Carregando agenda...');

        try {
            const parametros = new URLSearchParams({ medico_id: campoMedico.value, servico_id: campoServico.value });
            const resposta = await fetch(`/paciente/api/disponibilidade-calendario?${parametros}`);
            if (!resposta.ok) throw new Error('calendario_indisponivel');
            const dados = await resposta.json();

            gradeCalendario.replaceChildren();
            if (!Array.isArray(dados.dias) || dados.dias.length === 0) {
                mostrarMensagemCalendario(gradeCalendario, 'Nenhum dia disponível para essa combinação.');
                return;
            }

            dados.dias.forEach((dia) => {
                const botao = document.createElement('button');
                const diaSemana = document.createElement('span');
                const rotulo = document.createElement('strong');
                const vagas = document.createElement('small');

                botao.type = 'button';
                botao.className = `botao-dia-calendario ${dia.situacao === 'disponivel' ?'disponivel' : 'lotado'}`;
                diaSemana.textContent = dia.dia_semana;
                rotulo.textContent = dia.rotulo;
                vagas.textContent = dia.vagas_livres ?`${dia.vagas_livres} vagas` : 'sem vaga';

                botao.append(diaSemana, rotulo, vagas);
                botao.addEventListener('click', () => {
                    gradeCalendario.querySelectorAll('.botao-dia-calendario').forEach((item) => item.classList.remove('selecionado'));
                    botao.classList.add('selecionado');
                    campoData.value = dia.data;
                    if (rotuloData) rotuloData.textContent = dia.rotulo;
                    carregarHorarios();
                });

                gradeCalendario.appendChild(botao);
            });
        } catch (erro) {
            mostrarMensagemCalendario(gradeCalendario, 'Não foi possível carregar a agenda agora.');
        }
    }

    /**
     * Consulta a API e renderiza horários livres, ocupados e passados no dia escolhido.
     */
    async function carregarHorarios() {
        if (!campoMedico.value || !campoServico.value || !campoData.value) return;
        mostrarMensagemCalendario(gradeHorarios, 'Carregando horários...');

        try {
            const parametros = new URLSearchParams({ medico_id: campoMedico.value, servico_id: campoServico.value, data: campoData.value });
            const resposta = await fetch(`/paciente/api/disponibilidade?${parametros}`);
            if (!resposta.ok) throw new Error('horarios_indisponiveis');
            const dados = await resposta.json();

            gradeHorarios.replaceChildren();
            if (!Array.isArray(dados.horarios) || dados.horarios.length === 0) {
                mostrarMensagemCalendario(gradeHorarios, 'Nenhum horário encontrado para essa data.');
                return;
            }

            dados.horarios.forEach((itemHorario) => {
                const botao = document.createElement('button');
                botao.type = 'button';
                botao.className = `botao-horario ${itemHorario.disponivel ?'' : 'ocupado'} ${itemHorario.situacao === 'passado' ?'passado' : ''}`;
                botao.textContent = itemHorario.situacao === 'passado' ?`${itemHorario.horario} passou` : itemHorario.horario;
                botao.disabled = !itemHorario.disponivel;
                botao.addEventListener('click', () => {
                    gradeHorarios.querySelectorAll('.botao-horario').forEach((item) => item.classList.remove('selecionado'));
                    botao.classList.add('selecionado');
                    campoHorario.value = itemHorario.horario;
                    if (rotuloHorario) rotuloHorario.textContent = itemHorario.horario;
                });
                gradeHorarios.appendChild(botao);
            });
        } catch (erro) {
            mostrarMensagemCalendario(gradeHorarios, 'Não foi possível carregar horários agora.');
        }
    }

    /**
     * Aplica parâmetros vindos da página pública quando o usuário inicia agendamento antes do login.
     */
    function aplicarIntencaoDeAgendamento() {
        const parametros = new URLSearchParams(window.location.search);
        if (parametros.get('agendar') !== '1') return;

        const janela = document.getElementById('janela-planejador-consulta');
        if (janela) janela.classList.remove('hidden');

        const medicoId = parametros.get('medico_id');
        const servicoId = parametros.get('servico_id');

        if (medicoId) {
            const cartao = document.querySelector(`.cartao-escolha-medico[data-medico-id="${medicoId}"]`);
            if (cartao) cartao.click();
            else campoMedico.value = medicoId;
        }
        if (servicoId) {
            campoServico.value = servicoId;
            campoServico.dispatchEvent(new Event('change'));
        } else {
            carregarCalendario();
            carregarHorarios();
        }
    }
}

/**
 * Abre e fecha a janela de agendamento preservando foco e suporte ao Escape.
 */
function iniciarControlesJanelaConsulta() {
    const janela = document.getElementById('janela-planejador-consulta');
    if (!janela) return;

    const abrirJanela = () => {
        janela.classList.remove('hidden');
        janela.querySelector('select, input, button')?.focus();
    };
    const fecharJanela = () => {
        janela.classList.add('hidden');
    };

    document.querySelectorAll('[data-janela-consulta-abrir]').forEach((botao) => {
        botao.addEventListener('click', abrirJanela);
    });
    document.querySelectorAll('[data-janela-consulta-fechar]').forEach((botao) => {
        botao.addEventListener('click', fecharJanela);
    });
    document.addEventListener('keydown', (evento) => {
        if (evento.key === 'Escape' && !janela.classList.contains('hidden')) fecharJanela();
    });
}

/**
 * Configura formulários de remarcação e bloqueia envio para datas já passadas.
 */
function iniciarFormulariosRemarcacao() {
    const hoje = obterDataIsoDeHoje();

    document.querySelectorAll('[data-remarcacao-alternar]').forEach((botao) => {
        botao.addEventListener('click', () => {
            const formulario = document.querySelector(`[data-formulario-remarcacao="${botao.dataset.remarcacaoAlternar}"]`);
            if (!formulario) return;
            formulario.classList.toggle('hidden');
            if (!formulario.classList.contains('hidden')) {
                formulario.querySelector('input[name="data_consulta"]')?.focus();
            }
        });
    });

    document.querySelectorAll('.formulario-remarcacao').forEach((formulario) => {
        const campoData = formulario.querySelector('input[name="data_consulta"]');
        const campoHorario = formulario.querySelector('input[name="horario_consulta"]');
        if (campoData) campoData.setAttribute('min', hoje);
        formulario.addEventListener('submit', (evento) => {
            if (!campoData || !campoHorario) return;
            if (consultaJaPassou(campoData.value, campoHorario.value)) {
                evento.preventDefault();
                mostrarErroFormulario(formulario, 'Escolha uma data e horário futuros para remarcar.');
            }
        });
    });
}

/**
 * Permite marcar notificações como lidas sem recarregar todo o painel.
 */
function iniciarNotificacoesPaciente() {
    const central = document.querySelector('[data-central-notificacoes]');
    if (!central) return;

    const contador = document.getElementById('contador-notificacoes-paciente');
    const lista = central.querySelector('.lista-notificacoes');
    const botaoLerTodas = central.querySelector('[data-notificacoes-ler-todas]');

    central.querySelectorAll('[data-notificacao-ler]').forEach((botao) => {
        botao.addEventListener('click', async () => {
            const id = botao.dataset.notificacaoLer;
            const cartao = botao.closest('[data-cartao-notificacao]');
            if (!id || !cartao) return;

            botao.disabled = true;
            const sucesso = await enviarPostJson(`/paciente/notificacoes/${id}/ler`);
            if (sucesso) {
                cartao.remove();
                atualizarNotificacoes(lista, contador, botaoLerTodas);
            } else {
                botao.disabled = false;
            }
        });
    });

    if (botaoLerTodas) {
        botaoLerTodas.addEventListener('click', async () => {
            botaoLerTodas.disabled = true;
            const sucesso = await enviarPostJson('/paciente/notificacoes/ler-todas');
            if (sucesso) {
                central.querySelectorAll('[data-cartao-notificacao]').forEach((cartao) => cartao.remove());
                atualizarNotificacoes(lista, contador, botaoLerTodas);
            } else {
                botaoLerTodas.disabled = false;
            }
        });
    }
}

/**
 * Executa requisições POST simples usadas por ações assíncronas do painel.
 */
async function enviarPostJson(url) {
    try {
        const resposta = await fetch(url, { method: 'POST', headers: { 'X-Requested-With': 'fetch' } });
        return resposta.ok;
    } catch (erro) {
        return false;
    }
}

/**
 * Atualiza lista, contador e selo global depois de uma notificação ser lida.
 */
function atualizarNotificacoes(lista, contador, botaoLerTodas) {
    const restantes = document.querySelectorAll('[data-cartao-notificacao]').length;
    if (contador) contador.textContent = restantes;
    if (botaoLerTodas) botaoLerTodas.classList.toggle('hidden', restantes === 0);

    document.querySelectorAll('[data-selo-notificacao]').forEach((selo) => {
        selo.textContent = restantes;
        selo.classList.toggle('hidden', restantes === 0);
        selo.setAttribute('title', `Notificações não lidas: ${restantes}.`);
    });

    if (lista && restantes === 0 && !lista.querySelector('.estado-vazio-notificacao')) {
        const vazio = document.createElement('div');
        const titulo = document.createElement('strong');
        const texto = document.createElement('span');
        vazio.className = 'estado-vazio-notificacao';
        titulo.textContent = 'Tudo em dia.';
        texto.textContent = 'Nenhuma notificação nova no momento.';
        vazio.append(titulo, texto);
        lista.replaceChildren(vazio);
    }
}

/**
 * Substitui o conteúdo de uma grade de agenda por mensagem de estado.
 */
function mostrarMensagemCalendario(container, mensagem) {
    const elemento = document.createElement('div');
    elemento.className = 'carregando-calendario';
    elemento.textContent = mensagem;
    container.replaceChildren(elemento);
}

/**
 * Exibe erro inline no formulário sem depender de recarregamento da página.
 */
function mostrarErroFormulario(formulario, mensagem) {
    let erro = formulario.querySelector('.erro-formulario-inline');
    if (!erro) {
        erro = document.createElement('p');
        erro.className = 'erro-formulario-inline';
        formulario.appendChild(erro);
    }
    erro.textContent = mensagem;
}

/**
 * Gera a data atual em ISO local para uso em campos input[type=date].
 */
function obterDataIsoDeHoje() {
    const agora = new Date();
    agora.setMinutes(agora.getMinutes() - agora.getTimezoneOffset());
    return agora.toISOString().split('T')[0];
}

/**
 * Informa se a combinação de data e horário já ficou para trás.
 */
function consultaJaPassou(data, horario) {
    if (!data || !horario) return false;
    const consulta = new Date(`${data}T${horario}`);
    return !Number.isNaN(consulta.getTime()) && consulta <= new Date();
}

/**
 * Converte data ISO do formulário para formato brasileiro curto.
 */
function formatarDataCurta(valor) {
    if (!valor) return '--';
    const [ano, mes, dia] = valor.split('-');
    return `${dia}/${mes}/${ano}`;
}

/**
 * Atualiza contadores regressivos das próximas consultas do paciente.
 */
function iniciarContagens() {
    const caixas = document.querySelectorAll('.caixa-contagem[data-date]');
    if (!caixas.length) return;

    const atualizar = () => {
        caixas.forEach((caixa) => {
            const alvo = new Date(caixa.dataset.date.replace(' ', 'T'));
            const diferenca = alvo - new Date();
            if (Number.isNaN(diferenca) || diferenca <= 0) {
                caixa.textContent = 'Agora';
                return;
            }
            const horas = Math.floor(diferenca / 36e5);
            const dias = Math.floor(horas / 24);
            caixa.textContent = `${dias}d ${horas % 24}h ${Math.floor((diferenca % 36e5) / 6e4)}min`;
        });
    };

    atualizar();
    setInterval(atualizar, 60000);
}

/**
 * Renderiza gráficos compactos de sinais vitais quando Chart.js está disponível.
 */
function iniciarGraficosMiniatura() {
    if (typeof Chart === 'undefined') return;
    const metricas = window.metricasSaudeCardioLab || [];
    if (!metricas.length) return;

    const rotulos = metricas.map((_, indice) => indice + 1).reverse();
    const criarGrafico = (id, dados, cor) => {
        const canvas = document.getElementById(id);
        if (!canvas) return;
        new Chart(canvas, {
            type: 'line',
            data: { labels: rotulos, datasets: [{ data: dados.reverse(), borderColor: cor, borderWidth: 2, pointRadius: 0, tension: .35 }] },
            options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { x: { display: false }, y: { display: false } } }
        });
    };

    criarGrafico('spark-bp', metricas.map((item) => item.pressao_arterial ?parseInt(item.pressao_arterial.split('/')[0]) : null), '#D60000');
    criarGrafico('spark-hr', metricas.map((item) => item.frequencia_cardiaca), '#2563eb');
    criarGrafico('spark-peso', metricas.map((item) => item.peso ?Number(item.peso) : null), '#0f766e');
    criarGrafico('spark-glicemia', metricas.map((item) => item.glicemia ?Number(item.glicemia) : null), '#f59e0b');
}

/**
 * Escapa dados vindos de atributos HTML antes de montar trechos dinâmicos.
 */
function escaparHtml(valor) {
    return String(valor || '').replace(/[&<>"']/g, (caractere) => ({
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;',
    }[caractere]));
}
