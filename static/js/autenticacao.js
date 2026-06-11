/**
 * Prepara a tela de entrada e cadastro com máscaras, validações locais e
 * normalização de dados antes do envio ao servidor Flask.
 */
document.addEventListener('DOMContentLoaded', function() {
    iniciarAbasAutenticacao();
    iniciarMascaraCpf();
    iniciarMascaraTelefone();
    iniciarNormalizacaoEmail();
    iniciarMascaraCep();
});

/**
 * Alterna entre formulário de login e formulário de cadastro no mesmo template.
 */
function iniciarAbasAutenticacao() {
    const abas = document.querySelectorAll('.aba-autenticacao');
    const formularioEntrada = document.getElementById('formulario-entrada');
    const formularioCadastro = document.getElementById('formulario-cadastro');

    abas.forEach((aba) => {
        aba.addEventListener('click', () => {
            abas.forEach((item) => {
                item.classList.remove('ativo', 'text-primary', 'border-primary', 'border-b-2');
                item.classList.add('text-gray-400');
            });

            aba.classList.add('ativo', 'text-primary', 'border-primary', 'border-b-2');
            aba.classList.remove('text-gray-400');

            const mostrarEntrada = aba.dataset.aba === 'entrada';
            if (formularioEntrada) formularioEntrada.classList.toggle('hidden', !mostrarEntrada);
            if (formularioCadastro) formularioCadastro.classList.toggle('hidden', mostrarEntrada);
        });
    });
}

/**
 * Formata o CPF durante a digitação e executa validação local no campo.
 */
function iniciarMascaraCpf() {
    const campoCpf = document.getElementById('campo-cpf');
    if (!campoCpf) return;

    campoCpf.addEventListener('input', function(evento) {
        let valor = evento.target.value.replace(/\D/g, '');
        if (valor.length > 11) valor = valor.slice(0, 11);
        if (valor.length > 9) valor = valor.replace(/(\d{3})(\d{3})(\d{3})(\d{1,2})/, '$1.$2.$3-$4');
        else if (valor.length > 6) valor = valor.replace(/(\d{3})(\d{3})(\d{1,3})/, '$1.$2.$3');
        else if (valor.length > 3) valor = valor.replace(/(\d{3})(\d{1,3})/, '$1.$2');
        evento.target.value = valor;
    });

    campoCpf.addEventListener('blur', function() {
        const retorno = document.getElementById('retorno-cpf');
        if (!retorno || campoCpf.value.length !== 14) return;

        const valido = validarCpf(campoCpf.value);
        retorno.classList.remove('hidden');
        retorno.textContent = valido ? '✓ CPF válido' : '✗ CPF inválido';
        retorno.className = valido ? 'text-xs mt-1 text-green-600' : 'text-xs mt-1 text-red-600';
    });
}

/**
 * Aplica máscara brasileira de telefone sem alterar o valor enviado ao servidor.
 */
function iniciarMascaraTelefone() {
    const campoTelefone = document.getElementById('campo-telefone');
    if (!campoTelefone) return;

    campoTelefone.addEventListener('input', function(evento) {
        let valor = evento.target.value.replace(/\D/g, '');
        if (valor.length > 11) valor = valor.slice(0, 11);
        if (valor.length > 6) valor = valor.replace(/(\d{2})(\d{5})(\d{1,4})/, '($1) $2-$3');
        else if (valor.length > 2) valor = valor.replace(/(\d{2})(\d{1,5})/, '($1) $2');
        evento.target.value = valor;
    });
}

/**
 * Padroniza e-mails em letras minúsculas para reduzir duplicidade por variação.
 */
function iniciarNormalizacaoEmail() {
    document.querySelectorAll('input[type="email"]').forEach((campoEmail) => {
        campoEmail.addEventListener('blur', () => {
            campoEmail.value = campoEmail.value.trim().toLowerCase();
        });
    });
}

/**
 * Formata CEP e aciona consulta automática de endereço quando há oito dígitos.
 */
function iniciarMascaraCep() {
    const campoCep = document.getElementById('campo-cep');
    if (!campoCep) return;

    campoCep.addEventListener('input', function(evento) {
        let valor = evento.target.value.replace(/\D/g, '');
        if (valor.length > 8) valor = valor.slice(0, 8);
        if (valor.length > 5) valor = valor.replace(/(\d{5})(\d{1,3})/, '$1-$2');
        evento.target.value = valor;
    });

    campoCep.addEventListener('blur', function() {
        const cep = campoCep.value.replace(/\D/g, '');
        if (cep.length === 8) buscarCep(cep);
    });
}

/**
 * Valida CPF pelos dígitos verificadores oficiais.
 */
function validarCpf(cpf) {
    const digitos = cpf.replace(/\D/g, '');
    if (digitos.length !== 11) return false;
    if (/^(\d)\1{10}$/.test(digitos)) return false;

    let primeiraSoma = 0;
    for (let indice = 0; indice < 9; indice++) primeiraSoma += parseInt(digitos[indice]) * (10 - indice);
    const primeiroResto = primeiraSoma % 11;
    const primeiroDigito = primeiroResto < 2 ? 0 : 11 - primeiroResto;
    if (parseInt(digitos[9]) !== primeiroDigito) return false;

    let segundaSoma = 0;
    for (let indice = 0; indice < 10; indice++) segundaSoma += parseInt(digitos[indice]) * (11 - indice);
    const segundoResto = segundaSoma % 11;
    const segundoDigito = segundoResto < 2 ? 0 : 11 - segundoResto;
    return parseInt(digitos[10]) === segundoDigito;
}

/**
 * Consulta endereço pelo ViaCEP e fornece fallback local quando a API falha.
 */
function buscarCep(cep) {
    const campoEndereco = document.getElementById('campo-endereco');
    if (!campoEndereco) return;

    fetch(`https://viacep.com.br/ws/${cep}/json/`)
        .then((resposta) => resposta.json())
        .then((dados) => {
            if (!dados.erro) {
                campoEndereco.value = `${dados.logradouro || ''}, - ${dados.localidade || ''}/${dados.uf || ''}`;
            }
        })
        .catch(() => {
            campoEndereco.value = 'Endereço simulado - São Paulo/SP';
        });
}
