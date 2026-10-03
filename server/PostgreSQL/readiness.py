"""Read-only database readiness; never create a database or apply migrations."""
import argparse
from hashlib import sha256
import json
from pathlib import Path

import psycopg
from config import DEFAULT_CONFIG, load_config
from .postgres_db import DATABASE_ROOT, connection_options


def schema_issues(connection, requirements):
    """Inspect catalogs only; empty player tables are valid for a new save."""
    rows = connection.execute("""SELECT n.nspname || '.' || c.relname, a.attname,
        pg_catalog.format_type(a.atttypid, a.atttypmod), a.attnotnull
        FROM pg_catalog.pg_class c
        JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
        JOIN pg_catalog.pg_attribute a ON a.attrelid = c.oid
        WHERE n.nspname IN ('public', 'mog_local') AND c.relkind IN ('r', 'p')
          AND a.attnum > 0 AND NOT a.attisdropped""").fetchall()
    actual = {}
    for table, name, kind, not_null in rows:
        actual.setdefault(table, {})[name] = (kind, not_null)
    keys = connection.execute("""SELECT n.nspname || '.' || c.relname,
        array_agg(a.attname::text ORDER BY a.attname)
        FROM pg_catalog.pg_index i
        JOIN pg_catalog.pg_class c ON c.oid = i.indrelid
        JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
        CROSS JOIN LATERAL unnest(i.indkey) WITH ORDINALITY k(attnum, position)
        JOIN pg_catalog.pg_attribute a ON a.attrelid = c.oid AND a.attnum = k.attnum
        WHERE n.nspname IN ('public', 'mog_local') AND c.relkind IN ('r', 'p')
          AND i.indisunique AND i.indisvalid AND i.indisready
          AND i.indpred IS NULL AND i.indexprs IS NULL AND k.position <= i.indnkeyatts
        GROUP BY n.nspname, c.relname, i.indexrelid""").fetchall()
    unique = {}
    for table, columns in keys:
        unique.setdefault(table, set()).add(tuple(sorted(columns)))
    missing_tables, missing_columns, incompatible_columns, missing_keys = [], [], [], []
    for table, required in requirements.items():
        if table not in actual:
            missing_tables.append(table)
            continue
        for name, column in required["columns"].items():
            current = actual[table].get(name)
            if current is None:
                missing_columns.append(f"{table}.{name}")
            elif current != (column["type"], column["not_null"]):
                incompatible_columns.append(f"{table}.{name}")
        for columns in required["unique_keys"]:
            if tuple(sorted(columns)) not in unique.get(table, set()):
                missing_keys.append(f"{table}({','.join(columns)})")
    return {name: values for name, values in (
        ("missing_tables", missing_tables), ("missing_columns", missing_columns),
        ("incompatible_columns", incompatible_columns), ("missing_keys", missing_keys)) if values}


def inspect_database(settings):
    if not isinstance(settings, dict):
        return {"state": "error", "reason": "postgresql_required"}
    try:
        contract = json.loads((DATABASE_ROOT / "schema-contract.json").read_text(encoding="utf-8"))
        active = sorted((DATABASE_ROOT / "migrations").glob("*.sql"))
        checksums = {path.name: sha256(path.read_text(encoding="utf-8").encode()).hexdigest() for path in active}
        if contract["migrations"] != checksums or not contract["tables"]:
            return {"state": "error", "reason": "schema_contract_outdated"}
    except (OSError, ValueError, KeyError, TypeError):
        return {"state": "error", "reason": "schema_contract_outdated"}
    try:
        with psycopg.connect(**connection_options(settings)) as connection:
            connection.execute("SET TRANSACTION READ ONLY")
            connection.execute("SET LOCAL statement_timeout = '2000ms'")
            connection.execute("SET LOCAL lock_timeout = '1000ms'")
            available = connection.execute("SELECT to_regclass('mog_local.schema_migrations') IS NOT NULL").fetchone()[0]
            issues = schema_issues(connection, contract["tables"])
            if not available:
                return {"state": "error", "reason": "database_not_initialized",
                        **issues}
            # Check the ledger shape before selecting its columns.
            ledger_issues = {name: values for name, entries in issues.items()
                             if (values := [entry for entry in entries if entry.startswith("mog_local.schema_migrations")])}
            if ledger_issues:
                return {"state": "error", "reason": "database_schema_incomplete", **ledger_issues}
            applied = dict(connection.execute("SELECT version,checksum FROM mog_local.schema_migrations").fetchall())
            missing = []
            files = active + sorted((DATABASE_ROOT / "migrations/legacy").glob("*.sql"))
            if set(applied) - {path.name for path in files}:
                return {"state": "error", "reason": "database_version_newer_than_code"}
            for path in files:
                if path.name not in applied:
                    if path.parent.name != "legacy":
                        missing.append(path.name)
                    continue
                checksum = checksums.get(path.name)
                if checksum is None:
                    checksum = sha256(path.read_text(encoding="utf-8").encode()).hexdigest()
                if applied[path.name] != checksum:
                    return {"state": "error", "reason": "migration_checksum_mismatch"}
            if missing:
                return {"state": "error", "reason": "migrations_pending", "pending": len(missing),
                        "pending_migrations": missing, **issues}
            if issues:
                return {"state": "error", "reason": "database_schema_incomplete", **issues}
            return {"state": "pass", "reason": "standalone_ready", "migrations": len(applied),
                    "tables": len(contract["tables"]),
                    "columns": sum(len(table["columns"]) for table in contract["tables"].values())}
    except (OSError, ValueError, psycopg.Error):
        return {"state": "error", "reason": "database_connection_failed"}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args(argv)
    try:
        result = inspect_database(load_config(args.config).database)
    except (OSError, ValueError):
        result = {"state": "error", "reason": "invalid_database_config"}
    print(json.dumps(result))
    return 0 if result["state"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
