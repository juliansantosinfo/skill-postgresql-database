# Guia operacional

## Metadados

Listar tabelas: `SELECT table_schema, table_name FROM information_schema.tables WHERE table_type = 'BASE TABLE' AND table_schema NOT IN ('pg_catalog','information_schema') ORDER BY 1,2;`

Colunas: `SELECT column_name,data_type,is_nullable,column_default FROM information_schema.columns WHERE table_schema='public' AND table_name='exemplo' ORDER BY ordinal_position;`

Índices: `SELECT indexname,indexdef FROM pg_indexes WHERE schemaname='public' AND tablename='exemplo';`

Constraints: `SELECT conname,contype,pg_get_constraintdef(oid) FROM pg_constraint WHERE conrelid='public.exemplo'::regclass;`

## Sequência para DML/DDL
1. Confirme o banco/ambiente; inspecione schema e dependências.
2. Prepare SQL específico; evite `SELECT *`, consultas ilimitadas e escrita sem predicado.
3. Faça contagem e amostragem das linhas afetadas, quando aplicável.
4. Forneça ao usuário alvo, SQL/resumo, estimativa de impacto, riscos e estratégia de reversão.
5. Só execute `--apply --ack confirmed` se a confirmação corresponder ao plano concreto.
6. Valide estado posterior com consulta independente e registre o resultado.

## Observações técnicas
- `execute` sem `--apply` faz rollback de DML/DDL transacional, mas pode consumir sequências, obter locks, disparar integrações externas de trigger ou executar funções com efeitos fora do banco; **não execute uma prévia potencialmente perigosa sem autorização**.
- `fetchmany` limita saída mas não limita custo de processamento; acrescente LIMIT no SQL e examine EXPLAIN antes de consultas caras. Evite `EXPLAIN ANALYZE` inadvertido em instruções mutantes, pois ele executa a instrução.
- Reforce controle por papéis PostgreSQL distintos (somente leitura, escrita, migração) e contas com privilégio mínimo. A confirmação por flag protege contra acidentes no fluxo do agente, não contra um executor malicioso.
- `CREATE DATABASE`, `DROP DATABASE`, `VACUUM`, `CREATE INDEX CONCURRENTLY` e certos comandos administrativos precisam de fluxo separado, explicitamente aprovado e executado por um operador/rotina autorizada.
- Para bancos críticos, estabeleça backup verificável, migração versionada, observabilidade, auditoria, limites de conexão e janelas de manutenção.

## Portabilidade / psql
- Prefira `psql` no host onde o agente roda, no PATH ou `PGPSQL_PATH`, nunca dentro de um container arbitrário sem autorização.
- `PGCLIENT=auto` faz detecção, `PGCLIENT=python` força Psycopg. O wrapper requer `sqlparse` instalado.
- Para psql, saída é texto CSV truncado (64 KiB) e não há contagem estruturada garantida de linhas alteradas; confirme impacto por consulta posterior dentro das permissões autorizadas.
- Diferencie ausência de binário, indisponibilidade de rede e autenticação falha. Não altere variáveis de destino automaticamente.
