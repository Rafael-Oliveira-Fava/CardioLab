# Guia De Apresentação

Use este guia para dividir a fala entre quatro pessoas e apresentar o sistema de forma organizada.

## Divisão Para Quatro Pessoas

### Pessoa 1: Visão Geral E Site Público

Falar sobre:

- Objetivo do CardioLab.
- Página inicial, serviços, equipe, artigos, dúvidas e LGPD.
- Login, cadastro e modo escuro.

Arquivos para citar:

- `rotas/rotas_publicas.py`
- `templates/inicio.html`
- `templates/entrada.html`
- `static/css/site/`
- `static/css/autenticacao/`
- `static/js/portal_publico.js`

### Pessoa 2: Portal Do Paciente

Falar sobre:

- Painel inicial do paciente.
- Agendamento e remarcação de consultas.
- Bloqueio de dia ou horário já passado.
- Visualização/simulação de exames.
- Carteirinha CardioLab Care.

Arquivos para citar:

- `rotas/rotas_paciente.py`
- `templates/painel_paciente.html`
- `servicos/agenda.py`
- `servicos/carteirinha.py`
- `servicos/exames.py`
- `static/js/consultas_paciente.js`

### Pessoa 3: Painel Médico

Falar sobre:

- Agenda do médico.
- Pacientes do dia.
- Prontuários.
- Fila de atendimento.
- Teleconsulta.

Arquivos para citar:

- `rotas/rotas_medico.py`
- `templates/painel_medico_prontuarios.html`
- `static/js/medico_prontuarios.js`
- `servicos/exames.py`

### Pessoa 4: Administração, Segurança E Validação

Falar sobre:

- Cadastro administrativo de usuários.
- Validação de CPF/e-mail duplicado.
- Solicitação de nova senha pelo usuário.
- Redefinição de senha feita apenas pelo administrador.
- Aprovação de carteirinhas.
- Validações finais do sistema.

Arquivos para citar:

- `rotas/rotas_administracao.py`
- `rotas/rotas_autenticacao.py`
- `servicos/usuarios.py`
- `servicos/solicitacoes_senha.py`
- `templates/painel_administracao.html`

## Ordem Recomendada Da Demonstração

1. Abrir a página inicial.
2. Mostrar modo escuro.
3. Fazer login como paciente.
4. Mostrar painel do paciente, notificações, consultas, exames e carteirinha.
5. Mostrar tentativa de agendar/remarcar em horário inválido ou ocupado.
6. Entrar como médico e mostrar prontuários.
7. Entrar como administrador e mostrar usuários, carteirinhas e solicitações de senha.
8. Mostrar as verificações finais no terminal: compilação Python e checagem de JavaScript.

## Credenciais De Demonstração

As senhas de teste ficam padronizadas pelo script `corrigir_senhas.py`.

| Perfil | E-mail | Senha |
| --- | --- | --- |
| Paciente | `maria@email.com` | `cardiolab123` |
| Médico | `dr.ricardo@cardiolab.com.br` | `cardiolab123` |
| Administrador | `admin@cardiolab.com.br` | `cardiolab123` |

## Frases Simples Para Explicar

- "As rotas recebem a ação do usuário."
- "Os serviços guardam as regras importantes."
- "Os templates são as telas."
- "O static cuida do visual e das interações."
- "As verificações finais ajudam a confirmar que Python e JavaScript continuam sem erro de sintaxe."

## Pontos Fortes Para Destacar

- Cadastro bloqueia CPF ou e-mail repetido.
- Login aceita CPF ou e-mail.
- Senha não é redefinida por link inseguro: o administrador valida a solicitação.
- Agenda bloqueia horários passados e conflitos.
- Carteirinha simula um convênio interno CardioLab Care.
- Exames possuem tela de visualização/simulação.
- O CSS fica dividido em arquivos menores por área, facilitando leitura durante a apresentação.
- O projeto foi enxugado para a apresentação, mantendo os arquivos essenciais de funcionamento e documentação.

