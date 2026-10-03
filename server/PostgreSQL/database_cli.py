"""Create, import and inspect the local PostgreSQL database without API requests."""
import argparse
import json
from pathlib import Path
import sys

import psycopg
from psycopg import sql

from config import DEFAULT_CONFIG, load_config
from .db import Database
from local_server.replay import import_captures
from .postgres_db import connection_options


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--diagnostic-root", type=Path, help=argparse.SUPPRESS)
    commands = parser.add_subparsers(dest="command", required=True)
    initialize = commands.add_parser("init", help="Apply player-state and replay-storage migrations")
    initialize.add_argument("--create-database", action="store_true")
    initialize.add_argument("--sqlite", type=Path, help="Read-only import of the old replay database")
    initialize.add_argument("--capture", type=Path, nargs="*", help="Import captures; default: configured files")
    commands.add_parser("status")
    commands.add_parser("seed-players", help="Bootstrap missing public player states from the newest valid login snapshots")
    args = parser.parse_args(argv)
    try:
        config = load_config(args.config)
        if not isinstance(config.database, dict):
            parser.error("This command requires a PostgreSQL database configuration")
        if args.command == "status":
            from .readiness import inspect_database
            result = inspect_database(config.database)
            print(json.dumps(result))
            return 0 if result["state"] == "pass" else 1
        if config.standalone and (args.command == "seed-players" or getattr(args, "sqlite", None) or getattr(args, "capture", None)):
            parser.error("Standalone mode creates saves locally and does not import player responses")
        if args.command == "init" and args.create_database:
            options = connection_options(config.database)
            database_name = options["dbname"]
            options["dbname"] = "postgres"
            with psycopg.connect(**options, autocommit=True) as connection:
                if not connection.execute("SELECT 1 FROM pg_database WHERE datname=%s", (database_name,)).fetchone():
                    connection.execute(sql.SQL("CREATE DATABASE {} ENCODING 'UTF8' TEMPLATE template0").format(sql.Identifier(database_name)))
        database = Database(config.database)
        try:
            results = {}
            if args.command == "seed-players":
                results["player_import"] = database.players.seed_from_snapshots()
            if args.command == "init":
                if args.sqlite:
                    results["sqlite_import"] = database.import_sqlite(args.sqlite)
                captures = tuple(path.resolve() for path in args.capture) if args.capture is not None else config.captures
                if any(not path.is_file() for path in captures):
                    raise FileNotFoundError("Capture file missing")
                results["capture_responses_read"] = import_captures(database, captures, config.api_hosts)
            results.update(database.summary())
            print(json.dumps(results, ensure_ascii=False, indent=2))
        finally:
            database.close()
    except Exception as exc:
        # Driver messages may contain DSNs; keep CLI errors credential-free.
        # Flush inherited output before appending diagnostics through a separate
        # file handle, so buffered CLI output cannot overwrite the diagnostics.
        print("Database command failed:", type(exc).__name__, flush=True)
        if args.diagnostic_root is not None:
            project = str(Path(__file__).resolve().parents[2])
            if project not in sys.path:
                sys.path.append(project)
            try:
                from launcher.diagnostics import record_exception
                saved = record_exception(args.diagnostic_root, exc, context="数据库初始化",
                                         filename="database-setup.log")
            except Exception:
                saved = False
            if not saved:
                print("Database diagnostic log could not be written.", flush=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
