#!/usr/bin/env python3
"""PostgreSQL CLI portátil: prioriza psql do host, alternativamente Psycopg 3."""
import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


def load_project_env(explicit_path=None):
    """Load one .env: explicit > current project directory > skill root.

    Existing process environment variables retain precedence. Never combine
    project and skill .env files implicitly.
    """
    try:
        from dotenv import load_dotenv
    except ImportError as exc:
        raise ValueError("Instale python-dotenv: python -m pip install python-dotenv") from exc

    skill_root = Path(__file__).resolve().parent.parent
    if explicit_path is not None:
        env_path = Path(explicit_path).expanduser().resolve()
        if not env_path.is_file():
            raise ValueError("Arquivo --env-file não encontrado")
    else:
        project_env = Path.cwd() / ".env"
        skill_env = skill_root / ".env"
        env_path = project_env if project_env.is_file() else skill_env

    if env_path.is_file():
        load_dotenv(dotenv_path=env_path, override=False)
    return env_path if env_path.is_file() else None


def emit(data):
    print(json.dumps(data, ensure_ascii=False, default=str))


def settings():
    required = ("PGHOST", "PGDATABASE", "PGUSER", "PGPASSWORD")
    missing = [key for key in required if not os.environ.get(key)]
    if missing:
        raise ValueError("Variáveis ausentes: " + ", ".join(missing))
    port = int(os.getenv("PGPORT", "5432"))
    timeout = int(os.getenv("PGCOMMAND_TIMEOUT_MS", "15000"))
    if not (1 <= port <= 65535) or not (100 <= timeout <= 300000):
        raise ValueError("PGPORT ou PGCOMMAND_TIMEOUT_MS inválido")
    return port, timeout


def one_statement(sql):
    try:
        import sqlparse
    except ImportError as exc:
        raise ValueError("Instale sqlparse: python -m pip install sqlparse") from exc
    statements = sqlparse.split(sql, strip_semicolon=True)
    if len(statements) != 1 or not statements[0].strip():
        raise ValueError("Exatamente uma instrução SQL é permitida por chamada")
    return statements[0]


def resolve_psql():
    path = os.getenv("PGPSQL_PATH", "").strip()
    if path:
        executable = Path(path).expanduser()
        if not executable.is_file():
            raise ValueError("PGPSQL_PATH não aponta para um arquivo existente")
        return str(executable)
    return shutil.which("psql")


def psql_backend(args, sql, timeout_ms):
    executable = resolve_psql()
    if not executable:
        raise ValueError("psql não encontrado no PATH; configure PGPSQL_PATH ou use PGCLIENT=python")
    # SQL enviado por stdin: não aparece na linha de comando/process list.
    # -X ignora ~/.psqlrc; -w proíbe prompt; ON_ERROR_STOP faz erro SQL retornar código != 0.
    command = [executable, "-X", "-w", "--set=ON_ERROR_STOP=1", "--quiet", "--csv", "--file=-"]
    if args.command == "ping":
        sql = "SELECT current_database() AS database, current_user AS db_user, inet_server_addr() AS server_ip, inet_server_port() AS server_port;"
    elif args.command == "query":
        sql = "BEGIN READ ONLY;\n" + sql.rstrip(";\n ") + ";\nROLLBACK;\n"
    else:
        sql = "BEGIN;\n" + sql.rstrip(";\n ") + ";\n" + ("COMMIT;" if args.apply else "ROLLBACK;") + "\n"
    env = os.environ.copy()
    env["PGOPTIONS"] = f"-c statement_timeout={timeout_ms} -c lock_timeout=5000"
    try:
        completed = subprocess.run(command, input=sql, text=True, encoding="utf-8", errors="replace",
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env,
                                   timeout=max(15, timeout_ms / 1000 + 10), check=False)
    except subprocess.TimeoutExpired as exc:
        raise ValueError("Timeout do cliente psql; confirme no servidor se a transação foi concluída") from exc
    if completed.returncode:
        # STDERR pode incluir SQL/valores sensíveis. Não o incluímos no retorno.
        emit({"ok": False, "backend": "psql", "message": "Falha no psql. Verifique permissões, SQL e erros locais sem divulgar segredos", "exit_code": completed.returncode})
        return 1
    max_output = 65536
    emit({"ok": True, "backend": "psql", "mode": args.command,
          "output_csv": completed.stdout[:max_output], "truncated": len(completed.stdout) > max_output,
          "transaction": "read_only_completed" if args.command == "query" else
                         ("committed" if args.apply else "rolled_back") if args.command == "execute" else "not_applicable",
          "persisted": bool(args.command == "execute" and args.apply),
          "note": "A saída CSV de SELECT pode ser truncada; não interprete como conjunto completo de resultados."})
    return 0


def python_backend(args, sql, timeout_ms, port):
    try:
        import psycopg
        from psycopg.rows import dict_row
    except ImportError as exc:
        raise ValueError("Backend python exige psycopg: python -m pip install -r requirements.txt") from exc
    cfg = dict(host=os.environ["PGHOST"], port=port, dbname=os.environ["PGDATABASE"],
               user=os.environ["PGUSER"], password=os.environ["PGPASSWORD"],
               sslmode=os.getenv("PGSSLMODE", "prefer"), connect_timeout=5,
               options=f"-c statement_timeout={timeout_ms} -c lock_timeout=5000")
    try:
        with psycopg.connect(**cfg, autocommit=True, row_factory=dict_row) as conn:
            if args.command == "ping":
                with conn.cursor() as cur:
                    cur.execute("SELECT current_database() AS database, current_user AS db_user, inet_server_addr()::text AS server_ip, inet_server_port() AS server_port")
                    emit({"ok": True, "backend": "python", "connection": cur.fetchone()})
                return 0
            result = {}
            try:
                with conn.transaction():
                    if args.command == "query":
                        conn.execute("SET TRANSACTION READ ONLY")
                    with conn.cursor() as cur:
                        cur.execute(sql)
                        if cur.description:
                            records = cur.fetchmany(args.limit + 1)
                            result = {"ok": True, "backend": "python", "rows": records[:args.limit],
                                      "truncated": len(records) > args.limit}
                        else:
                            result = {"ok": True, "backend": "python", "rowcount": cur.rowcount}
                    if args.command == "execute" and not args.apply:
                        raise PreviewRollback()
            except PreviewRollback:
                result.update(transaction="rolled_back", persisted=False)
            else:
                result.update(transaction="read_only_completed" if args.command == "query" else "committed",
                              persisted=args.command == "execute")
            emit(result)
            return 0
    except psycopg.Error:
        emit({"ok": False, "backend": "python", "message": "Erro PostgreSQL (detalhes omitidos para proteger possíveis segredos)"})
        return 1


class PreviewRollback(Exception):
    pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, help="Caminho explícito do .env; padrão: projeto/.env, senão skill/.env")
    parser.add_argument("--client", choices=("auto", "psql", "python"), default=None)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("ping")
    for name in ("query", "execute"):
        cmd = sub.add_parser(name)
        group = cmd.add_mutually_exclusive_group(required=True)
        group.add_argument("--file", type=Path)
        group.add_argument("--sql")
        cmd.add_argument("--limit", type=int, default=100)
        if name == "execute":
            cmd.add_argument("--apply", action="store_true")
            cmd.add_argument("--ack", choices=("confirmed",))
    args = parser.parse_args()
    try:
        load_project_env(args.env_file)
        port, timeout_ms = settings()
        if args.command != "ping" and not 1 <= args.limit <= 1000:
            raise ValueError("--limit deve estar entre 1 e 1000")
        if args.command == "execute" and args.apply and args.ack != "confirmed":
            raise ValueError("Aplicar exige aprovação humana e --apply --ack confirmed")
        sql = one_statement(args.file.read_text(encoding="utf-8") if args.file else args.sql) if args.command != "ping" else None
        client = args.client or os.getenv("PGCLIENT", "auto")
        if client not in ("auto", "psql", "python"):
            raise ValueError("PGCLIENT deve ser auto, psql ou python")
        if client == "auto":
            client = "psql" if resolve_psql() else "python"
        if client == "psql":
            return psql_backend(args, sql, timeout_ms)
        return python_backend(args, sql, timeout_ms, port)
    except (OSError, ValueError) as exc:
        emit({"ok": False, "error": str(exc)})
        return 1


if __name__ == "__main__":
    sys.exit(main())
