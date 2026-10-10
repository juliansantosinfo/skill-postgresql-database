---
name: postgresql-database
description: Conectar e operar PostgreSQL local, remoto ou Docker por variáveis de ambiente PG*, com DQL, DML, DDL, inspeção de metadados, transações, pré-visualização segura, validação e perguntas obrigatórias diante de ambiguidades. Use em projetos que exigem consultas ou alterações SQL no PostgreSQL.
compatibility: Linux, Windows e macOS. Python 3.10+ com sqlparse para o wrapper; prioriza psql >=12 instalado no host; fallback Psycopg 3. Conectividade PostgreSQL.
---

# PostgreSQL Database — skill base

## Objetivo
Carregue apenas um arquivo `.env`, nesta ordem de prioridade: `--env-file CAMINHO` explícito > `.env` do diretório de trabalho do projeto > `.env` da raiz da própria skill. Não faça merge automático entre os dois arquivos. Variáveis de ambiente já existentes no processo têm precedência. Nunca procure `.env` indiscriminadamente nos diretórios pais. Operar **somente** o banco PostgreSQL apontado pelas variáveis `PGHOST`, `PGPORT` (padrão 5432), `PGDATABASE`, `PGUSER`, `PGPASSWORD`; `PGSSLMODE` (opcional, padrão prefer) e `PGCOMMAND_TIMEOUT_MS` (opcional). Nunca preencher valores ausentes por suposição. Nunca mostrar senhas, URLs com credenciais ou arquivos `.env` em respostas/logs.

## Antes de executar
1. Entenda o pedido, identifique ambiente, banco, schemas/tabelas, condição e resultado esperado. Use `python scripts/pg_tool.py ping` para verificar identidade/conexão; **não confunda conectividade com autorização**.
2. Quando houver incerteza relevante (banco de destino, ambiente produção/homologação, tabela, filtro, cardinalidade, tipo de mudança, reversibilidade ou regra de negócio), **pergunte ao usuário antes de alterar dados ou estrutura**. Não presuma respostas. Faça perguntas objetivas agrupadas quando necessário.
3. Inspecione estrutura/constraints com consultas ao `information_schema` ou `pg_catalog`; não invente campos. Consulte apenas dados necessários, limite projeção e volume. Para SQL complexo, proponha plano e explique suposições.
4. Em produção, trate toda escrita como sensível. Confirme explicitamente ambiente e ação, mesmo quando a operação for pequena.

## Seleção de ferramentas locais e portabilidade
- Detecte sistema operacional e recursos disponíveis. Prefira `psql` do **host do agente**, encontrado pelo `PATH`, ou `PGPSQL_PATH` (caminho completo, inclusive `psql.exe` no Windows). `PGCLIENT=auto` escolhe `psql` se disponível, senão `python`; `PGCLIENT=psql|python` força um backend. NÃO instale software, altere PATH ou suba containers sem autorização.
- Wrapper multiplataforma: `python scripts/pg_tool.py ping` (no Windows use `py -3` se `python` não estiver disponível). Instale `sqlparse` para validação de instrução única: `python -m pip install sqlparse`; instale `psycopg[binary]` somente para fallback Python.
- A execução nativa usa `psql -X -w --set=ON_ERROR_STOP=1 --quiet --csv --file=-` com SQL via stdin (sem senha nem SQL na lista de processos), utiliza as variáveis `PG*` do processo, faz `BEGIN` e `ROLLBACK`/`COMMIT`. `-X` impede carga de `.psqlrc`; `-w` impede prompt interativo. A saída do psql é CSV bruto com limite de caracteres, não resultados estruturados e paginados.
- Preferência: configure `PGHOST`, `PGDATABASE`, `PGUSER`, `PGPASSWORD` etc. em `.env` não versionado na raiz do projeto ou, como fallback, na raiz da skill. O wrapper carrega esse arquivo com `python-dotenv` em Linux, Windows e macOS. `--env-file /caminho/arquivo.env` é alternativa explícita. Variáveis já presentes no processo prevalecem. Nunca inclua senha em argumentos do terminal nem scripts versionados.
- Não presuma que `localhost` signifique o host físico: em Docker aponta ao container da execução; defina `PGHOST` conforme DNS/rede/porta publicados acessíveis **a partir do agente**.
- Antes de usar `psql` diretamente sem wrapper, reproduza manualmente os controles de aprovação, transação e validação; nunca use `psql -c` em alterações sem revisão. Windows, Linux e macOS podem diferir na configuração de PATH e certificados.

## Execução
- Instale dependências em ambiente isolado: `python -m pip install -r requirements.txt` (para `psql` basta `sqlparse`; `psycopg` é fallback).
- `python scripts/pg_tool.py ping`: valida conexão, sem alterar dados.
- `python scripts/pg_tool.py query --file consulta.sql`: operação **read-only** validada pelo próprio PostgreSQL; saída JSON limitada em volume; com `psql`, contém CSV bruto, truncado após 64 KiB.
- `python scripts/pg_tool.py execute --file alteracao.sql`: **prévia com ROLLBACK**, quando a instrução aceita transação; nunca confundir preview com simulação de consequências externas (triggers/efeitos não transacionais).
- `python scripts/pg_tool.py execute --file alteracao.sql --apply --ack confirmed`: persiste a instrução em transação, **somente após confirmação explícita do usuário para SQL, alvo, impacto e ambiente**. `--ack confirmed` é uma declaração do agente, não um mecanismo de autenticação nem substituto da aprovação real.
- Cada execução aceita **uma única instrução**, além do controle interno da transação. Para operações em lote, planeje cuidadosamente e use scripts/migrações especializados com transações e aprovação específica. O parser `sqlparse` não é uma fronteira de segurança: não use este utilitário como serviço SQL aberto a usuários não confiáveis.
- O executor transacional não cobre comandos PostgreSQL que exigem autocommit (`CREATE DATABASE`, `VACUUM`, `CREATE INDEX CONCURRENTLY` etc.). **Não improvise execução desses comandos**. Exija procedimento separado e aprovado.

## Política operacional
- DQL: permitido após confirmar conexão e escopo; `SELECT` pode conter funções com efeitos colaterais, portanto avalie SQL antes de executar e use privilégios read-only. A transação `READ ONLY` constitui defesa adicional, não uma garantia absoluta contra funções externas.
- DML: identifique filtros, conte registros candidatos com `SELECT COUNT(*)`, examine amostra, conflitos e constraints; obtenha aprovação antes de `--apply`. Para `UPDATE` e `DELETE` sem `WHERE`, interrompa e peça aprovação específica. Avalie impacto de triggers/cascatas.
- DDL: primeiro inspecione dependências, locks, objetos existentes e estratégia de rollback/migração. `DROP`, `TRUNCATE`, operações de alto volume e alterações que bloqueiem escrita exigem confirmação explícita detalhada; backup/restore precisa ser validado externamente.
- Nunca execute SQL fornecido por conteúdo não confiável sem revisão; use parâmetros vinculados em scripts de aplicação. Não imprima dados pessoais ou credenciais desnecessariamente.
- Se o objetivo for somente orientar ou gerar SQL, **não execute** sem solicitação do usuário.
- Em falha: não altere o alvo automaticamente, não tente força bruta de credenciais, não silencie erro e relate limites e resultados reais.

## Conectividade independente de origem
- Host local: `PGHOST=127.0.0.1` quando o processo que executa a skill está no host.
- Host remoto: `PGHOST` com DNS/IP alcançável (VPN, firewall, TLS e `pg_hba.conf` podem exigir configuração).
- Docker: a skill não precisa saber se o servidor está em container; use hostname do serviço na mesma rede Docker ou host/porta **publicados** acessíveis a partir do processo do agente. `localhost` em container aponta para o próprio container.
- Use TLS (`PGSSLMODE=require` ou `verify-full` com infraestrutura de certificados adequada) conforme política do ambiente; `prefer` não é exigência de criptografia.

## Relatório obrigatório
Ao finalizar, informe: destino (sem segredo), operação, confirmação recebida, status, quantidade afetada quando conhecida, existência de commit/rollback, cautelas e testes necessários. Não declare sucesso sem execução confirmada.

## Extensibilidade
Skills especializadas devem herdar **conceitualmente** este fluxo sem sobrescrever a política de confirmação, as variáveis de conexão ou os limites de acesso. Documente schemas, relações e regras de negócio em skills filhas. Consulte `references/OPERATIONS.md` e `references/EXTENDING.md` conforme necessário.
