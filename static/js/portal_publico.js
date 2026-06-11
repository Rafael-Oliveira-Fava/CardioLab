/**
 * Inicializa os comportamentos globais do site público e da estrutura base.
 */
document.addEventListener('DOMContentLoaded', () => {
    iniciarMenuMobile();
    iniciarCabecalhoRolagem();
    iniciarRevelacaoRolagem();
    iniciarContadores();
    iniciarMensagensTemporarias();
    iniciarMovimentoDestaque();
    iniciarPreviaRisco();
    iniciarCarrosselDepoimentos();
    iniciarFluxoNotificacoes();
    iniciarCuidadosMovimento();
    iniciarBotoesSenha();
    iniciarFormulariosConfirmaveis();
});

/**
 * Controla abertura, fechamento e acessibilidade do menu mobile.
 */
function iniciarMenuMobile() {
    const botaoMenu = document.getElementById('botao-menu-mobile');
    const menuMobile = document.getElementById('menu-mobile');
    if (!botaoMenu || !menuMobile) return;

    const definirMenuAberto = (aberto) => {
        // O botão precisa refletir o estado do menu para navegação por teclado.
        menuMobile.classList.toggle('hidden', !aberto);
        botaoMenu.setAttribute('aria-expanded', String(aberto));
        botaoMenu.setAttribute('aria-label', aberto ?'Fechar menu' : 'Abrir menu');
    };

    botaoMenu.addEventListener('click', () => {
        definirMenuAberto(menuMobile.classList.contains('hidden'));
    });

    menuMobile.querySelectorAll('a').forEach((link) => {
        link.addEventListener('click', () => definirMenuAberto(false));
    });

    document.addEventListener('keydown', (evento) => {
        if (evento.key === 'Escape' && !menuMobile.classList.contains('hidden')) {
            definirMenuAberto(false);
            botaoMenu.focus();
        }
    });
}

/**
 * Aplica estado visual ao cabeçalho quando a página é rolada.
 */
function iniciarCabecalhoRolagem() {
    const cabecalho = document.getElementById('cabecalho-principal');
    if (!cabecalho) return;

    const atualizarCabecalho = () => {
        cabecalho.classList.toggle('cabecalho-rolado', window.scrollY > 24);
    };

    atualizarCabecalho();
    window.addEventListener('scroll', atualizarCabecalho, { passive: true });
}

/**
 * Revela elementos progressivamente quando entram na área visível da tela.
 */
function iniciarRevelacaoRolagem() {
    const elementos = document.querySelectorAll('.revelar-rolagem');
    if (!elementos.length) return;

    const observador = new IntersectionObserver((entradas) => {
        entradas.forEach((entrada) => {
            if (!entrada.isIntersecting) return;
            entrada.target.classList.add('revelado');
            observador.unobserve(entrada.target);
        });
    }, { threshold: 0.08, rootMargin: '0px 0px -40px 0px' });

    elementos.forEach((elemento) => observador.observe(elemento));
}

/**
 * Dispara contadores numéricos apenas quando os indicadores ficam visíveis.
 */
function iniciarContadores() {
    const contadores = document.querySelectorAll('.contador');
    if (!contadores.length) return;

    const observador = new IntersectionObserver((entradas) => {
        entradas.forEach((entrada) => {
            if (!entrada.isIntersecting) return;
            const contador = entrada.target;
            const alvo = parseInt(contador.getAttribute('data-alvo'), 10) || 0;
            animarContador(contador, alvo);
            observador.unobserve(contador);
        });
    }, { threshold: 0.5 });

    contadores.forEach((contador) => observador.observe(contador));
}

/**
 * Anima um número inteiro até o valor final apresentado em estatísticas.
 */
function animarContador(elemento, alvo) {
    let atual = 0;
    const incremento = Math.max(1, Math.ceil(alvo / 60));
    const temporizador = setInterval(() => {
        atual += incremento;
        if (atual >= alvo) {
            atual = alvo;
            clearInterval(temporizador);
        }
        elemento.textContent = atual.toLocaleString('pt-BR');
    }, 30);
}

/**
 * Remove mensagens de flash depois de alguns segundos e permite fechamento manual.
 */
function iniciarMensagensTemporarias() {
    setTimeout(() => {
        const recipiente = document.getElementById('recipiente-mensagens');
        if (!recipiente) return;
        recipiente.style.transition = 'opacity 0.5s';
        recipiente.style.opacity = '0';
        setTimeout(() => recipiente.remove(), 500);
    }, 5000);

    document.querySelectorAll('[data-fechar-mensagem]').forEach((botao) => {
        botao.addEventListener('click', () => botao.closest('.mensagem-temporaria')?.remove());
    });
}

/**
 * Aplica deslocamento leve ao bloco visual do destaque sem afetar o conteúdo.
 */
function iniciarMovimentoDestaque() {
    const videoDestaque = document.querySelector('.container-video-destaque');
    if (!videoDestaque) return;

    window.addEventListener('scroll', () => {
        const rolagem = window.scrollY;
        if (rolagem < 900) {
            videoDestaque.style.transform = `translateY(${rolagem * 0.06}px)`;
        }
    }, { passive: true });
}

/**
 * Conecta botões de mostrar/ocultar senha aos campos declarados no HTML.
 */
function iniciarBotoesSenha() {
    document.querySelectorAll('[data-alternar-senha]').forEach((botao) => {
        botao.addEventListener('click', () => alternarSenha(botao.dataset.alternarSenha));
    });
}

/**
 * Alterna o tipo de um campo entre senha e texto.
 */
function alternarSenha(idCampo) {
    const campo = document.getElementById(idCampo);
    if (!campo) return;
    campo.type = campo.type === 'password' ?'text' : 'password';
}

/**
 * Exige confirmação antes de enviar formulários com ação sensível.
 */
function iniciarFormulariosConfirmaveis() {
    document.querySelectorAll('[data-confirmar-envio]').forEach((formulario) => {
        formulario.addEventListener('submit', (evento) => {
            if (!confirm(formulario.dataset.confirmarEnvio)) evento.preventDefault();
        });
    });
}

/**
 * Calcula uma prévia pública de risco cardiovascular usando a API do backend.
 */
function iniciarPreviaRisco() {
    const formulario = document.getElementById('formulario-previa-risco');
    const resultado = document.getElementById('resultado-previa-risco');
    if (!formulario || !resultado) return;

    formulario.addEventListener('submit', async (evento) => {
        evento.preventDefault();
        const dados = new FormData(formulario);
        const carga = Object.fromEntries(dados.entries());
        carga.trata_pressao = dados.has('trata_pressao');
        carga.fumante = dados.has('fumante');
        carga.diabetes = dados.has('diabetes');
        resultado.textContent = 'Calculando...';

        try {
            const resposta = await fetch('/api/risco/framingham', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(carga)
            });
            if (!resposta.ok) throw new Error('calculo_risco_falhou');

            const json = await resposta.json();
            const rotuloRisco = json.classe_risco === 'intermediario' ?'intermediário' : json.classe_risco;
            const destaque = document.createElement('strong');
            const primeiraRecomendacao = Array.isArray(json.recomendacoes) && json.recomendacoes.length
                ?` · ${json.recomendacoes[0]}`
                : '';

            destaque.textContent = `${json.risco_percentual}%`;
            resultado.replaceChildren(
                destaque,
                document.createTextNode(` em 10 anos · risco ${rotuloRisco} · média populacional ${json.media_populacional_percentual}%${primeiraRecomendacao}`)
            );
        } catch (erro) {
            resultado.textContent = 'Não foi possível calcular agora.';
        }
    });
}

/**
 * Mantém o carrossel de depoimentos em rotação automática.
 */
function iniciarCarrosselDepoimentos() {
    const carrossel = document.getElementById('carrossel-depoimentos');
    if (!carrossel) return;

    setInterval(() => {
        const rolagemMaxima = carrossel.scrollWidth - carrossel.clientWidth;
        if (carrossel.scrollLeft >= rolagemMaxima - 8) {
            carrossel.scrollTo({ left: 0, behavior: 'smooth' });
        } else {
            carrossel.scrollBy({ left: 340, behavior: 'smooth' });
        }
    }, 4200);
}

/**
 * Abre conexão SSE para atualizar notificações de usuários autenticados.
 */
function iniciarFluxoNotificacoes() {
    if (!window.EventSource || !document.body.dataset.authenticated) return;

    let ultimaNotificacaoId = 0;
    const fluxo = new EventSource('/api/fluxo');
    fluxo.addEventListener('notificacoes', (evento) => {
        const carga = JSON.parse(evento.data);
        atualizarSelosNotificacao(carga.nao_lidas, carga.atualizado_em);

        const ultima = carga.notificacoes && carga.notificacoes[0];
        if (ultima && Number(ultima.id) !== ultimaNotificacaoId) {
            ultimaNotificacaoId = Number(ultima.id);
            mostrarAviso(ultima.titulo, ultima.mensagem, ultima.tipo);
        }
    });
}

/**
 * Atualiza os contadores visuais de notificações não lidas.
 */
function atualizarSelosNotificacao(total, atualizadoEm) {
    document.querySelectorAll('[data-selo-notificacao]').forEach((selo) => {
        selo.textContent = total;
        selo.classList.toggle('hidden', Number(total) === 0);
        selo.dataset.atualizadoEm = atualizadoEm || new Date().toISOString();
        selo.setAttribute('title', `Notificações não lidas: ${total}. Atualizado agora.`);
    });
}

/**
 * Exibe aviso flutuante para eventos recentes recebidos em tempo real.
 */
function mostrarAviso(titulo, mensagem, tipo = 'informacao') {
    const recipiente = document.getElementById('container-aviso') || criarRecipienteAvisos();
    const aviso = document.createElement('div');
    const classeTipo = {
        info: 'informacao',
        success: 'sucesso',
        warning: 'alerta',
        reminder: 'lembrete',
        danger: 'perigo'
    }[tipo] || tipo;

    const tituloElemento = document.createElement('strong');
    const mensagemElemento = document.createElement('span');
    aviso.className = `aviso-flutuante ${classeTipo}`;
    tituloElemento.textContent = titulo;
    mensagemElemento.textContent = mensagem || '';
    aviso.append(tituloElemento, mensagemElemento);
    recipiente.appendChild(aviso);
    setTimeout(() => aviso.remove(), 5200);
}

/**
 * Cria o recipiente de avisos quando a página ainda não possui um.
 */
function criarRecipienteAvisos() {
    const recipiente = document.createElement('div');
    recipiente.id = 'container-aviso';
    document.body.appendChild(recipiente);
    return recipiente;
}

/**
 * Respeita preferência de movimento reduzido e tenta reproduzir vídeos decorativos.
 */
function iniciarCuidadosMovimento() {
    const movimentoReduzido = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    document.documentElement.classList.toggle('movimento-reduzido-ativo', !!movimentoReduzido);

    document.querySelectorAll('video[autoplay]').forEach((video) => {
        const tentarReproduzir = () => {
            const tentativa = video.play && video.play();
            if (tentativa && typeof tentativa.catch === 'function') {
                tentativa.catch(() => {
                    video.setAttribute('data-reproducao-bloqueada', 'true');
                });
            }
        };

        if (video.readyState >= 2) tentarReproduzir();
        else video.addEventListener('canplay', tentarReproduzir, { once: true });
    });
}
