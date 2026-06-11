# Banco De Dados

O banco principal é MySQL. O arquivo `banco_de_dados.sql` cria as tabelas e dados de demonstração.

## Tabelas Principais

- `usuarios`: contas do sistema, incluindo pacientes, médicos e administradores.
- `pacientes`: dados complementares de pacientes.
- `medicos`: dados complementares de médicos.
- `servicos`: serviços e exames oferecidos pela clínica.
- `consultas`: consultas agendadas.
- `prontuarios`: prontuários médicos.
- `resultados_exames`: resultados de exames.
- `notificacoes`: avisos do sistema para o usuário.
- `auditoria`: registros de ações importantes.
- `planos_carteirinha`: planos CardioLab Care.
- `carteirinhas_pacientes`: carteirinhas solicitadas ou ativas.
- `solicitacoes_senha`: pedidos de nova senha tratados pelo administrador.
- `calculos_risco`: cálculos de risco cardiovascular.

## Segurança De Senha

O sistema não usa mais envio de link por e-mail.

Fluxo atual:

1. Usuário solicita nova senha em `/recuperar-senha`.
2. O pedido fica salvo em `solicitacoes_senha`.
3. O administrador acessa o painel.
4. O administrador define uma senha temporária.
5. O sistema atualiza `usuarios.senha_hash`.

## Dados De Demonstração

O arquivo `banco_de_dados.sql` inclui usuários de teste. Se precisar padronizar senhas depois de importar o banco, execute:

```bash
python corrigir_senhas.py
```

## Padrão De Nomes

As tabelas e colunas do banco foram substituídas por nomes em português sem acentos, como `usuarios`, `consultas`, `situacao`, `titulo`, `mensagem`, `codigo`, `biografia`, `observacoes` e `medicamentos`.

O código próprio foi alinhado com esse padrão. Foram mantidas apenas palavras obrigatórias das tecnologias usadas, como `Flask`, `HTML`, `CSS`, `JavaScript`, `id`, `type`, `class`, `status` HTTP e `filename` em cabeçalhos de arquivo.



