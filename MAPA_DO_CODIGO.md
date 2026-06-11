# Mapa Simples Do Código CardioLab

Este arquivo é o ponto de partida para entender o projeto sem precisar saber programação a fundo.

## Ideia Geral

O CardioLab é um sistema web feito em Flask. Ele é dividido em quatro camadas:

1. `rotas/`: recebe acessos, cliques e formulários.
2. `servicos/`: guarda as regras importantes do sistema.
3. `templates/`: monta as telas em HTML.
4. `static/`: guarda CSS, JavaScript, imagens e arquivos enviados.

## Como Ler O Projeto

Se você quer entender uma funcionalidade, siga este caminho:

1. Ache a tela em `templates/`.
2. Ache a rota relacionada em `rotas/`.
3. Ache a regra reaproveitável em `servicos/`.
4. Ache o visual ou a interação em `static/`.

Exemplo: a carteirinha aparece em `templates/painel_paciente.html`, é acionada por `rotas/rotas_paciente.py`, usa regras de `servicos/carteirinha.py` e tem visual nos arquivos de `static/css/painel/`.

## Pastas Principais

- `rotas/`: ações do site, como login, cadastro, painel do paciente, painel médico e administração.
- `servicos/`: regras de negócio, como CPF, agenda, carteirinha, exames, senha e risco cardíaco.
- `templates/`: páginas HTML que o usuário vê.
- `static/css/`: aparência do site.
- `static/js/`: interações no navegador.

## Arquivos Maiores

Alguns arquivos ainda são grandes porque concentram telas completas:

- `rotas/rotas_paciente.py`: todas as ações do portal do paciente.
- `templates/painel_paciente.html`: todas as abas do painel do paciente.
- `rotas/rotas_medico.py`: agenda, pacientes, prontuário e teleconsulta do médico.
- `banco_de_dados.sql`: estrutura inicial do banco e dados de demonstração.
- `static/js/consultas_paciente.js`: calendário, horários e remarcação.

Esses arquivos não foram divididos agora para evitar risco perto da entrega. Este mapa e o guia de apresentação explicam onde cada parte principal fica.

## Fluxos Mais Importantes

- Cadastro: valida CPF, e-mail, senha e duplicidade.
- Login: aceita e-mail ou CPF.
- Recuperação de senha: o usuário solicita e o administrador redefine.
- Agenda: bloqueia horários passados e horários ocupados.
- Carteirinha: paciente solicita plano CardioLab Care e admin aprova.
- Exames: paciente visualiza resultado ou tela de manutenção/simulação.
- Médico: acompanha consultas, prontuários e pacientes.
- Administração: gerencia usuários, carteirinhas, relatórios e segurança.

## Nomes Técnicos

O banco de dados e o código próprio usam nomes em português sempre que isso não depende de uma palavra obrigatória da tecnologia. As tabelas principais usam nomes como `usuarios`, `pacientes`, `medicos`, `servicos`, `consultas`, `prontuarios`, `resultados_exames`, `notificacoes`, `planos_carteirinha` e `carteirinhas_pacientes`.

As telas também receberam chaves de contexto em português, como `consultas_hoje`, `proximas_consultas`, `nome_servico`, `nome_medico`, `situacao`, `notificacoes`, `carteirinha` e `aba_ativa`.

Algumas palavras aparecem por obrigação da própria ferramenta, como `Flask`, `HTML`, `CSS`, `JavaScript`, `id`, `class`, `type`, `href`, `script`, `status` HTTP e `filename` em cabeçalhos de arquivo. Elas não representam regras do sistema; são palavras reservadas ou contratos externos.

Quando o sistema mostra situação de consulta, carteirinha ou perfil para o usuário, os rótulos passam por `servicos/rotulos.py`.



