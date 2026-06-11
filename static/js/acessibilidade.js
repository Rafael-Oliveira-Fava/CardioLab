let nivelFonte = 0;
const CHAVE_PREFERENCIAS_ACESSIBILIDADE = 'cardiolab-acessibilidade';

/**
 * Conecta o painel de acessibilidade aos controles globais da interface.
 * A inicialização também restaura preferências salvas no navegador do usuário.
 */
document.addEventListener('DOMContentLoaded', function() {
    const menu = document.getElementById('menu-acessibilidade');
    const botao = document.getElementById('botao-acessibilidade');
    const painel = document.getElementById('painel-acessibilidade');

    if (botao && painel) {
        const definirPainelAberto = (aberto) => {
            // Mantém o estado visual do painel sincronizado com leitores de tela.
            painel.classList.toggle('hidden', !aberto);
            botao.setAttribute('aria-expanded', String(aberto));
        };

        botao.addEventListener('click', () => {
            definirPainelAberto(painel.classList.contains('hidden'));
        });

        document.addEventListener('click', (evento) => {
            if (!menu || painel.classList.contains('hidden')) return;
            if (!menu.contains(evento.target)) definirPainelAberto(false);
        });

        document.addEventListener('keydown', (evento) => {
            if (evento.key === 'Escape' && !painel.classList.contains('hidden')) {
                definirPainelAberto(false);
                botao.focus();
            }
        });
    }

    document.querySelectorAll('[data-alterar-fonte]').forEach((controle) => {
        controle.addEventListener('click', () => alterarTamanhoFonte(Number(controle.dataset.alterarFonte)));
    });
    document.querySelectorAll('[data-alternar-contraste]').forEach((controle) => {
        controle.addEventListener('click', alternarContraste);
    });
    document.querySelectorAll('[data-alternar-tema]').forEach((controle) => {
        controle.addEventListener('click', alternarModoEscuro);
    });
    document.querySelectorAll('[data-redefinir-acessibilidade]').forEach((controle) => {
        controle.addEventListener('click', redefinirAcessibilidade);
    });

    const preferencias = carregarPreferencias();
    if (preferencias.nivelFonte) {
        nivelFonte = preferencias.nivelFonte;
        aplicarTamanhoFonte();
    }
    if (preferencias.altoContraste) {
        document.body.classList.add('alto-contraste');
    }
    if (preferencias.modoEscuro) {
        document.documentElement.classList.add('tema-escuro');
    }
    atualizarControlesTema();
});

/**
 * Altera a escala base da página dentro de limites controlados.
 * O limite evita que a interface quebre em telas pequenas ou em painéis densos.
 */
function alterarTamanhoFonte(direcao) {
    nivelFonte += direcao;
    if (nivelFonte < -2) nivelFonte = -2;
    if (nivelFonte > 4) nivelFonte = 4;
    aplicarTamanhoFonte();
    salvarPreferencias();
}

/**
 * Aplica o tamanho de fonte calculado no elemento raiz do documento.
 */
function aplicarTamanhoFonte() {
    document.body.classList.remove('fonte-grande', 'fonte-muito-grande');
    const tamanhoBase = 16 + (nivelFonte * 2);
    document.documentElement.style.fontSize = tamanhoBase + 'px';
}

/**
 * Alterna a classe de alto contraste usada pelo CSS de acessibilidade.
 */
function alternarContraste() {
    document.body.classList.toggle('alto-contraste');
    salvarPreferencias();
}

/**
 * Alterna o modo escuro e atualiza todos os botões que representam o tema.
 */
function alternarModoEscuro() {
    document.documentElement.classList.toggle('tema-escuro');
    atualizarControlesTema();
    salvarPreferencias();
}

/**
 * Remove preferências locais e devolve a interface ao padrão visual inicial.
 */
function redefinirAcessibilidade() {
    nivelFonte = 0;
    document.documentElement.style.fontSize = '';
    document.documentElement.classList.remove('tema-escuro');
    document.body.classList.remove('alto-contraste', 'fonte-grande', 'fonte-muito-grande');
    localStorage.removeItem(CHAVE_PREFERENCIAS_ACESSIBILIDADE);
    atualizarControlesTema();
}

/**
 * Persiste as preferências de acessibilidade no armazenamento local do navegador.
 */
function salvarPreferencias() {
    localStorage.setItem(CHAVE_PREFERENCIAS_ACESSIBILIDADE, JSON.stringify({
        nivelFonte: nivelFonte,
        altoContraste: document.body.classList.contains('alto-contraste'),
        modoEscuro: document.documentElement.classList.contains('tema-escuro')
    }));
}

/**
 * Recupera preferências salvas e ignora dados corrompidos no localStorage.
 */
function carregarPreferencias() {
    try {
        return JSON.parse(localStorage.getItem(CHAVE_PREFERENCIAS_ACESSIBILIDADE) || '{}');
    } catch (erro) {
        localStorage.removeItem(CHAVE_PREFERENCIAS_ACESSIBILIDADE);
        return {};
    }
}

/**
 * Atualiza rótulos, atributos ARIA e símbolos dos botões de tema.
 */
function atualizarControlesTema() {
    const modoEscuro = document.documentElement.classList.contains('tema-escuro');
    document.querySelectorAll('[data-alternar-tema]').forEach((controle) => {
        const rotulo = modoEscuro ? 'Modo claro' : 'Modo escuro';
        controle.setAttribute('aria-pressed', String(modoEscuro));
        controle.setAttribute('aria-label', rotulo);
        controle.title = rotulo;
        controle.classList.toggle('esta-ativo', modoEscuro);
        controle.querySelectorAll('.botao-tema').forEach((botaoTema) => {
            botaoTema.classList.toggle('esta-ativo', modoEscuro);
        });

        const alvoRotulo = controle.querySelector('[data-rotulo-tema]');
        if (alvoRotulo) alvoRotulo.textContent = rotulo;

        const simbolo = controle.querySelector('.simbolo-tema');
        if (simbolo) simbolo.textContent = modoEscuro ? '☀' : '◐';

        if (!alvoRotulo && !controle.querySelector('.icone-tema')) {
            controle.textContent = modoEscuro ? '☀ Modo claro' : '◐ Modo escuro';
        }
    });
}
