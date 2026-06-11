/**
 * Associa a calculadora cardiovascular aos botões presentes nas páginas do portal.
 */
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('[data-calcular-risco]').forEach((botao) => {
        botao.addEventListener('click', calcularRisco);
    });
});

/**
 * Coleta fatores clínicos, envia ao backend e renderiza o resultado estimado.
 * O cálculo definitivo fica no servidor para manter a regra médica centralizada.
 */
async function calcularRisco() {
    const dados = {
        idade: Number(document.getElementById('risco-idade').value),
        sexo: document.getElementById('risco-sexo').value,
        pressao_sistolica: Number(document.getElementById('risco-pressao').value),
        colesterol_total: Number(document.getElementById('risco-colesterol').value),
        hdl: Number(document.getElementById('risco-hdl').value),
        trata_pressao: document.getElementById('risco-trata-pressao').checked,
        fumante: document.getElementById('risco-fumante').checked,
        diabetes: document.getElementById('risco-diabetes').checked
    };

    const resultado = document.getElementById('resultado-risco');
    if (!resultado) return;

    if (!dados.idade || !dados.pressao_sistolica || !dados.colesterol_total || !dados.hdl) {
        resultado.className = 'p-3 rounded-lg text-center text-sm font-semibold bg-yellow-50 text-yellow-700';
        resultado.textContent = 'Preencha todos os campos obrigatórios.';
        resultado.classList.remove('hidden');
        return;
    }

    resultado.className = 'p-3 rounded-lg text-center text-sm font-semibold bg-blue-50 text-blue-700';
    resultado.textContent = 'Calculando...';
    resultado.classList.remove('hidden');

    try {
        const resposta = await fetch('/paciente/api/calculos-risco', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(dados)
        });
        if (!resposta.ok) throw new Error('calculo_risco_falhou');

        const risco = await resposta.json();
        const classes = {
            baixo: 'baixo',
            intermediario: 'medio',
            alto: 'alto'
        };
        const textos = {
            baixo: 'Estimativa baixa para eventos cardiovasculares em 10 anos. Mantenha acompanhamento preventivo e hábitos protetores.',
            intermediario: 'Estimativa intermediária. Vale discutir metas de pressão, colesterol e glicemia com seu cardiologista.',
            alto: 'Estimativa alta. Procure avaliação cardiológica para um plano intensivo de redução de risco.'
        };
        const rotulos = {
            baixo: 'baixo',
            intermediario: 'intermediário',
            alto: 'alto'
        };
        const recomendacoes = Array.isArray(risco.recomendacoes) ?risco.recomendacoes.slice(0, 3) : [];

        resultado.className = `cartao-resultado-risco ${classes[risco.classe_risco] || classes.baixo}`;

        const topo = document.createElement('div');
        const percentual = document.createElement('strong');
        const rotulo = document.createElement('span');
        const texto = document.createElement('p');
        const media = document.createElement('small');

        topo.className = 'topo-resultado-risco';
        percentual.textContent = `${risco.risco_percentual}%`;
        rotulo.textContent = `Risco ${rotulos[risco.classe_risco] || risco.classe_risco}`;
        texto.textContent = textos[risco.classe_risco] || textos.baixo;
        media.textContent = `Média populacional comparável: ${risco.media_populacional_percentual}%.`;
        topo.append(percentual, rotulo);

        const elementos = [topo, texto, media];
        if (recomendacoes.length) {
            const lista = document.createElement('ul');
            recomendacoes.forEach((item) => {
                const linha = document.createElement('li');
                linha.textContent = item;
                lista.appendChild(linha);
            });
            elementos.push(lista);
        }

        resultado.replaceChildren(...elementos);
    } catch (erro) {
        resultado.className = 'p-3 rounded-lg text-center text-sm font-semibold bg-red-50 text-red-700';
        resultado.textContent = 'Não foi possível calcular o risco agora.';
    }
}
