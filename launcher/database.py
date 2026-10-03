"""Database tool entry point sharing the launcher's saved credential."""
import argparse
import os
from pathlib import Path
import subprocess
import sys

from .credentials import CredentialError, database_environment

ROOT = Path(__file__).resolve().parents[1]


def main(argv=None, *, root=ROOT):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("status", "init"))
    parser.add_argument("--create-database", action="store_true")
    args = parser.parse_args(argv)
    if args.create_database and args.action != "init":
        parser.error("--create-database 只能用于 init")
    module = "PostgreSQL.readiness" if args.action == "status" else "PostgreSQL.database_cli"
    arguments = [sys.executable, "-B", "-m", module, "--config", str(root / "runtime/server.config.json")]
    if args.action == "init":
        arguments.append("init")
        if args.create_database:
            arguments.append("--create-database")
    try:
        return subprocess.run(arguments, cwd=root / "server", env=database_environment(root),
                              creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0).returncode
    except CredentialError as exc:
        print(str(exc))
        return 2
    except OSError:
        print("数据库工具无法启动，请先完成一键配置。")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
