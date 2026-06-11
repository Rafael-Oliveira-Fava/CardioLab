/**
 * Inicializa todos os componentes de abas declarados com data-painel-raiz.
 * Cada painel mantém seu estado ativo por URL, atributos de acessibilidade e
 * evento customizado para integrações internas.
 */
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('[data-painel-raiz]').forEach(iniciarAbasPainel);
});

/**
 * Controla um conjunto de abas dentro de um painel administrativo, médico ou paciente.
 * A função associa botões, painéis de conteúdo, navegação por teclado e persistência
 * do identificador da aba na query string.
 */
function iniciarAbasPainel(raiz) {
    const abas = [...raiz.querySelectorAll('[data-aba-painel]')];
    const paineis = [...raiz.querySelectorAll('[data-painel-aba]')];
    if (!abas.length || !paineis.length) return;

    const listaAbas = raiz.querySelector('[data-abas-painel]');
    const abasNavegacao = abas.filter((aba) => aba.closest('[data-abas-painel]'));
    const idsValidos = new Set(paineis.map((painel) => painel.dataset.painelAba));
    const parametros = new URLSearchParams(window.location.search);
    const abaRequisitada = parametros.get('aba') || raiz.dataset.abaPadrao;
    const abaInicial = idsValidos.has(abaRequisitada) ?abaRequisitada : paineis[0].dataset.painelAba;

    const ativar = (idAba, atualizarUrl = true) => {
        // Centraliza a troca de aba para manter botões, painéis e URL sincronizados.
        if (!idsValidos.has(idAba)) return;

        abas.forEach((aba) => {
            const ativa = aba.dataset.abaPainel === idAba;
            const abaNavegacao = Boolean(aba.closest('[data-abas-painel]'));
            aba.classList.toggle('ativo', ativa);
            if (abaNavegacao) {
                aba.setAttribute('aria-selected', String(ativa));
                aba.setAttribute('tabindex', ativa ?'0' : '-1');
            }
        });

        paineis.forEach((painel) => {
            const ativo = painel.dataset.painelAba === idAba;
            painel.hidden = !ativo;
            painel.classList.toggle('ativo', ativo);
        });

        if (atualizarUrl) {
            const url = new URL(window.location.href);
            url.searchParams.set('aba', idAba);
            window.history.replaceState({}, '', url);
        }

        window.dispatchEvent(new CustomEvent('cardiolab:aba-painel-alterada', { detail: { idAba } }));
    };

    if (listaAbas) listaAbas.setAttribute('role', 'tablist');
    abas.forEach((aba) => {
        const abaNavegacao = Boolean(aba.closest('[data-abas-painel]'));
        if (abaNavegacao) {
            const painel = paineis.find((item) => item.dataset.painelAba === aba.dataset.abaPainel);
            const idAba = aba.id || `${raiz.id || 'painel'}-aba-${aba.dataset.abaPainel}`;
            const idPainel = painel?.id || `${raiz.id || 'painel'}-painel-${aba.dataset.abaPainel}`;
            aba.id = idAba;
            aba.setAttribute('role', 'tab');
            aba.setAttribute('aria-controls', idPainel);
            if (painel) {
                painel.id = idPainel;
                painel.setAttribute('aria-labelledby', idAba);
            }
        }
        aba.addEventListener('click', () => ativar(aba.dataset.abaPainel));
    });

    paineis.forEach((painel) => painel.setAttribute('role', 'tabpanel'));
    abasNavegacao.forEach((aba, indice) => {
        aba.addEventListener('keydown', (evento) => {
            const teclas = ['ArrowLeft', 'ArrowRight', 'Home', 'End'];
            if (!teclas.includes(evento.key)) return;
            evento.preventDefault();

            let proximoIndice = indice;
            if (evento.key === 'ArrowLeft') proximoIndice = (indice - 1 + abasNavegacao.length) % abasNavegacao.length;
            if (evento.key === 'ArrowRight') proximoIndice = (indice + 1) % abasNavegacao.length;
            if (evento.key === 'Home') proximoIndice = 0;
            if (evento.key === 'End') proximoIndice = abasNavegacao.length - 1;

            abasNavegacao[proximoIndice].focus();
            ativar(abasNavegacao[proximoIndice].dataset.abaPainel);
        });
    });

    ativar(abaInicial, false);
}
