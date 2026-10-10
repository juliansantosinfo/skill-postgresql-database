## Configuração via .env (preferencial)

Crie `.env` na **raiz do projeto** (diretório de execução) ou na **raiz da skill**, baseado em `.env.example`. O wrapper carrega automaticamente **um único arquivo** com `python-dotenv`, sem exportar credenciais globalmente e sem sobrescrever variáveis já definidas no processo. A prioridade é: `--env-file` explícito > `.env` da raiz do projeto > `.env` da raiz da skill. Se existir o `.env` do projeto, o da skill **não** será carregado, mesmo que faltem campos no primeiro. **Não é necessário `source` ou `export`.** O mesmo ambiente é repassado ao subprocesso `psql` quando utilizado.

```bash
python -m pip install -r requirements.txt
python .agents/skills/postgresql-database/scripts/pg_tool.py ping
python .agents/skills/postgresql-database/scripts/pg_tool.py query --sql "SELECT version()"
```

No Windows PowerShell substitua `python` por `py -3` se necessário. Para apontar um arquivo fora da raiz do projeto:

```bash
python .agents/skills/postgresql-database/scripts/pg_tool.py --env-file ./config/banco.env ping
```

O parâmetro `--env-file` deve vir **antes** de `ping`, `query` ou `execute`. Nunca versionar `.env`/`banco.env` contendo credenciais. Use `.gitignore` no projeto e certifique-se de que os arquivos de configuração sensíveis não foram adicionados anteriormente ao Git.

---

# postgresql-database — skill multiplataforma

Base para agentes de IA operarem PostgreSQL em Linux, Windows ou macOS, com acesso via `psql` do host e fallback Python/Psycopg. Independente de onde o **servidor** PostgreSQL esteja instalado (local, remoto ou Docker); requer conectividade alcançável do host que executa a skill.

## Requisitos
- Python 3.10+ e `sqlparse` para o wrapper: `python -m pip install sqlparse`.
- Preferencial: `psql` v12+ instalado no **host** e acessível no `PATH`.
- Alternativa: `python -m pip install -r requirements.txt` (inclui Psycopg).
- Configure `PGHOST`, `PGDATABASE`, `PGUSER`, `PGPASSWORD` e opcionais `PGPORT`, `PGSSLMODE`, `PGCOMMAND_TIMEOUT_MS` como variáveis do processo. Nunca salve senhas no repositório.
- `PGCLIENT=auto` (padrão), `psql` ou `python`. `PGPSQL_PATH` opcional para indicar executável fora do `PATH`.

## Linux/macOS (Bash/zsh)
```bash
export PGHOST=127.0.0.1 PGPORT=5432 PGDATABASE=app_db PGUSER=app_agent
# Defina PGPASSWORD pelo seu gerenciador de segredos, sem incluir no histórico.
python3 -m pip install sqlparse
python3 scripts/pg_tool.py ping
python3 scripts/pg_tool.py query --sql 'SELECT current_database(), current_user'
```

## Windows PowerShell
```powershell
$env:PGHOST='127.0.0.1'; $env:PGPORT='5432'
$env:PGDATABASE='app_db'; $env:PGUSER='app_agent'
# Defina PGPASSWORD fora do histórico, pelo gerenciador de segredos.
py -3 -m pip install sqlparse
py -3 scripts/pg_tool.py ping
py -3 scripts/pg_tool.py query --sql 'SELECT current_database(), current_user'
# Se necessário: $env:PGPSQL_PATH='C:\Program Files\PostgreSQL\17\bin\psql.exe'
```

## Alterações (mesma sintaxe em todos os sistemas)
```bash
python scripts/pg_tool.py execute --file examples/update_example.sql
# Somente após aprovação explícita de SQL, impacto e destino:
python scripts/pg_tool.py execute --file examples/update_example.sql --apply --ack confirmed
```

`--ack confirmed` não autentica o usuário e não substitui aprovação. O executor sem `--apply` faz rollback, mas gatilhos externos/efeitos não transacionais podem existir; a prévia não é um ambiente de simulação perfeito. Backends têm formatos distintos: `psql` retorna CSV bruto limitado; Psycopg retorna até `--limit` registros estruturados. Não execute operações SQL administrativas incompatíveis com transações. Veja `SKILL.md`.
