# CardioLab

Sistema web para clínica de cardiologia, com site público, portal do paciente, painel médico, painel administrativo, carteirinha CardioLab Care, exames, agenda e fluxo seguro de solicitação de nova senha.

## Tecnologias

- Python 3
- Flask
- MySQL
- Jinja2
- HTML, CSS e JavaScript
- Tailwind CSS via CDN
- Chart.js via CDN
- APScheduler
- ReportLab e pypdf

## Documentos Para Entender O Projeto

- `GUIA_APRESENTACAO.md`: roteiro para apresentar em quatro pessoas.
- `MAPA_DO_CODIGO.md`: explicação simples da estrutura do código.
- `BANCO_DE_DADOS.md`: explicação das tabelas principais.

## Instalação

1. Instale Python 3.
2. Instale MySQL.
3. Instale as dependências:

```bash
pip install -r dependencias.txt
```

4. Importe o banco:

```bash
mysql -u root -p < banco_de_dados.sql
```

5. Configure o MySQL em `configuracao.py`, se necessário:

```python
MYSQL_HOST = "localhost"
MYSQL_USER = "root"
MYSQL_PASSWORD = ""
MYSQL_DB = "cardiolab"
```

6. Padronize as senhas de demonstração:

```bash
python corrigir_senhas.py
```

7. Rode o sistema:

```bash
python aplicacao.py
```

Acesse: `http://127.0.0.1:5000`

## Credenciais De Demonstração

| Perfil | E-mail | Senha |
| --- | --- | --- |
| Paciente | `maria@email.com` | `cardiolab123` |
| Médico | `dr.ricardo@cardiolab.com.br` | `cardiolab123` |
| Administrador | `admin@cardiolab.com.br` | `cardiolab123` |

## Recuperação De Senha

O sistema não envia link por e-mail.

Fluxo atual:

1. Usuário clica em "Esqueci minha senha".
2. Usuário informa e-mail ou CPF.
3. O pedido aparece no painel administrativo.
4. O administrador valida e cria uma senha temporária.
5. O usuário recebe a senha temporária por um canal seguro definido pela clínica.

## Verificações

Execute:

```bash
python -m compileall aplicacao.py configuracao.py configuracao_logs.py extensoes.py rotas servicos tarefas.py corrigir_senhas.py
```

Verifique JavaScript:

```powershell
Get-ChildItem static\js -Filter *.js | ForEach-Object { node --check $_.FullName }
```

## Estrutura Resumida

```text
cardiolab/
├── aplicacao.py
├── configuracao.py
├── banco_de_dados.sql
├── rotas/
├── servicos/
├── templates/
├── static/
├── GUIA_APRESENTACAO.md
├── MAPA_DO_CODIGO.md
└── BANCO_DE_DADOS.md
```

## Observação Sobre Nomes Técnicos

O banco de dados usa nomes em português, como `usuarios`, `consultas`, `servicos`, `situacao`, `titulo` e `mensagem`. Alguns nomes continuam em inglês apenas quando são contratos técnicos de URL, endpoint Flask, CSS, template ou JavaScript, como `/paciente`, `/medico`, `/administracao` e `paciente.painel`.



