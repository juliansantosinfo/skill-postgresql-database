# Criando skills específicas por sistema

Exemplo: `erp-estoque-postgresql/SKILL.md`.

1. Descreva quando ativar a skill especializada e declare dependência operacional de `postgresql-database`.
2. Documente schemas, tabelas e relacionamentos verificados no banco (sem inventar estrutura).
3. Acrescente regras de negócio, validações de domínio, exemplos SQL revisados e testes.
4. Não copie segredos, não sobrescreva variáveis PG* e não elimine exigências de confirmação para escrita.
5. Se forem necessárias transações multi-instrução ou parâmetros dinâmicos, crie script próprio com Psycopg e parâmetros vinculados; mantenha aprovação explícita e testes.
6. A presença de uma skill base não implica herança automática: o sistema de agentes precisa carregar/ler as duas skills ou declarar dependência nas instruções.
