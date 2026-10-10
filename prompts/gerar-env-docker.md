# Tarefa: Gerar arquivos .env para instâncias PostgreSQL em Docker

Você é um agente de IA especializado em Linux, Docker e PostgreSQL.

## Objetivo

Identificar as instâncias PostgreSQL executadas em containers Docker neste host Linux e gerar um arquivo `.env` individual para cada instância, seguindo o padrão utilizado pela skill `postgresql-database`.

## 1. Descoberta das instâncias

Utilize as ferramentas disponíveis no host, como:

- `docker ps`
- `docker inspect`
- `docker port`
- `docker compose config`, quando aplicável
- `pg_isready` e `psql`, quando disponíveis

Identifique todos os containers PostgreSQL, incluindo aqueles que utilizam imagens personalizadas.

Para cada instância, obtenha:

- Nome e ID do container
- Imagem PostgreSQL utilizada
- Versão do PostgreSQL, quando possível
- Host acessível a partir do terminal Linux
- Porta publicada no host
- Nome do banco de dados
- Usuário de autenticação
- Senha de autenticação, quando disponível nas configurações existentes
- Configuração SSL/TLS

Considere variáveis como `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_PASSWORD_FILE` e configurações de Docker Compose.

Não presuma que as variáveis de inicialização representam necessariamente o estado atual do banco. Valide a conexão sempre que possível.

Se alguma informação não puder ser determinada com segurança, pergunte ao usuário antes de prosseguir. Não invente credenciais.

Não exponha senhas, secrets ou outras informações confidenciais nos logs ou no relatório final.

## 2. Geração dos arquivos

Crie o diretório:

`./postgresql-connections/`

Para cada instância, gere um arquivo com o padrão:

`<nome-do-container>.env`

Sanitize o nome do arquivo para evitar caracteres inválidos ou caminhos inseguros.

Cada arquivo deve seguir esta estrutura:

```dotenv
# PostgreSQL
PGHOST=127.0.0.1
PGPORT=5432
PGDATABASE=nome_do_banco
PGUSER=usuario
PGPASSWORD=senha

# Cliente
PGCLIENT=auto

# Segurança
PGSSLMODE=prefer
PGCOMMAND_TIMEOUT_MS=30000
```

Regras importantes:

1. Utilize a porta publicada no host para `PGPORT`, e não necessariamente a porta interna 5432 do container.
2. Prefira `127.0.0.1` para containers publicados localmente, desde que a conexão funcione.
3. Se não houver porta publicada ou o acesso depender de outra rede, apresente a situação e solicite orientação antes de modificar qualquer configuração.
4. Configure `PGCLIENT=auto`.
5. Não desative SSL/TLS caso a instância exija conexão segura.
6. Não sobrescreva arquivos `.env` existentes sem autorização.
7. Restrinja as permissões dos arquivos a `600`.
8. Nunca inclua senhas no relatório final.

## 3. Validação

Após gerar cada arquivo:

- Verifique a existência das variáveis obrigatórias.
- Valide a acessibilidade do host e da porta.
- Teste a autenticação usando as credenciais do arquivo.
- Execute uma consulta somente leitura:

```sql
SELECT
    current_database() AS database_name,
    current_user AS connected_user,
    version() AS postgres_version;
```

Execute os testes sem imprimir credenciais.

Se a skill `postgresql-database` estiver disponível, utilize preferencialmente seu executor com o parâmetro `--env-file`.

Caso contrário, utilize o `psql` instalado no host.

Não execute comandos DDL ou DML durante a validação.

## 4. Relatório final

Apresente uma tabela com:

- Container
- Versão do PostgreSQL
- Endereço de conexão
- Porta
- Banco de dados
- Usuário
- Caminho do arquivo `.env`
- Resultado da validação

Não exiba senhas.

## 5. Segurança e comportamento

- Não interrompa nem reinicie containers.
- Não modifique arquivos Docker Compose.
- Não altere usuários, senhas ou permissões no PostgreSQL.
- Não crie ou exclua bancos de dados.
- Não modifique portas ou redes Docker.
- Não copie arquivos de secrets para diretórios públicos.
- Não inclua os `.env` no controle de versão.
- Se houver dúvidas, inconsistências ou múltiplas configurações possíveis, questione o usuário antes de tomar decisões.

Ao concluir, informe quais instâncias estão prontas para serem utilizadas pela skill `postgresql-database` e quais necessitam de intervenção.
