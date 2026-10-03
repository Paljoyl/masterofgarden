"""Discover installed PostgreSQL and prepare only a project-owned cluster."""
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import tempfile

from .environment import EnvironmentSetupError, owned_path

FLAGS = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0


class PostgresSetupError(RuntimeError):
    pass


def listening(port):
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=.25):
            return True
    except OSError:
        return False


def installed_bins():
    candidates = []
    executable = shutil.which("pg_ctl")
    if executable:
        candidates.append(Path(executable).parent)
    for name in ("ProgramFiles", "ProgramFiles(x86)"):
        directory = Path(os.environ.get(name, "C:/Program Files")) / "PostgreSQL"
        if directory.is_dir():
            candidates.extend(child / "bin" for child in directory.iterdir() if child.is_dir())
    if os.name == "nt":
        import winreg
        for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
            for view in (winreg.KEY_WOW64_64KEY, winreg.KEY_WOW64_32KEY):
                try:
                    with winreg.OpenKey(hive, r"SOFTWARE\PostgreSQL\Installations", 0, winreg.KEY_READ | view) as key:
                        for index in range(winreg.QueryInfoKey(key)[0]):
                            with winreg.OpenKey(key, winreg.EnumKey(key, index)) as installation:
                                base, _ = winreg.QueryValueEx(installation, "Base Directory")
                                candidates.append(Path(base) / "bin")
                except OSError:
                    continue
    suffix = ".exe" if os.name == "nt" else ""
    found = []
    for directory in dict.fromkeys(candidates):
        if not all((directory / (name + suffix)).is_file() for name in ("postgres", "pg_ctl", "initdb")):
            continue
        try:
            result = subprocess.run([str(directory / ("postgres" + suffix)), "--version"],
                                    capture_output=True, timeout=5, creationflags=FLAGS)
            match = re.search(rb"PostgreSQL\) (\d+)(?:\.(\d+))?", result.stdout)
            if result.returncode == 0 and match:
                found.append((int(match[1]), directory))
        except (OSError, subprocess.TimeoutExpired):
            continue
    return sorted(found, key=lambda item: item[0], reverse=True)


def ensure_postgres(root, port, user, password, progress=lambda text: None):
    if listening(port):
        progress("本机目标端口已有监听，将验证当前数据库连接设置。")
        return
    try:
        data = owned_path(root, Path(root) / "runtime/postgres")
        log = owned_path(root, Path(root) / "runtime/logs/postgres.log")
        marker = data / "PG_VERSION"
        major = int(marker.read_text(encoding="ascii").strip()) if marker.is_file() else None
        candidates = installed_bins()
        binary = next((path for version, path in candidates if major is None or version == major), None)
        if binary is None:
            raise PostgresSetupError("未找到兼容的 PostgreSQL 程序，请安装 PostgreSQL 后重试；启动器会自动选择程序位置。")
        progress("已自动选择 PostgreSQL 程序。")
        log.parent.mkdir(parents=True, exist_ok=True)
        suffix = ".exe" if os.name == "nt" else ""

        def run(name, arguments, message, timeout):
            with log.open("ab") as output:
                result = subprocess.run([str(binary / (name + suffix)), *arguments], stdout=output, stderr=output,
                                        timeout=timeout, creationflags=FLAGS,
                                        env=dict(os.environ, PYTHONUTF8="1"))
            if result.returncode:
                raise PostgresSetupError(message + "失败，请查看运行日志中的数据库程序输出。")

        if major is None:
            if not password or any(character in password for character in "\r\n\x00"):
                raise PostgresSetupError("自动创建数据库实例需要单行非空密码，请重新填写。")
            if data.exists() and any(data.iterdir()):
                raise PostgresSetupError("本项目数据库目录不完整，已保留文件；请检查后重试。")
            progress("正在创建本项目独立数据库实例…")
            # initdb needs a short-lived password file; it never enters command arguments or logs.
            with tempfile.TemporaryDirectory(prefix="mog-pg-password-") as directory:
                password_file = Path(directory) / "password"
                password_file.write_text(password + "\n", encoding="utf-8")
                run("initdb", ["-D", str(data), "-U", user, "--auth=scram-sha-256", "--no-locale",
                               "-E", "UTF8", "--pwfile", str(password_file)], "数据库实例初始化", 120)
        progress("正在启动本项目数据库实例…")
        # pg_ctl receives one option string; only validated integer port and fixed host are included.
        result = subprocess.run([str(binary / ("pg_ctl" + suffix)), "-D", str(data), "-l", str(log),
                                 "-o", f"-h 127.0.0.1 -p {port}", "-w", "-t", "30", "start"],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=40, creationflags=FLAGS)
        if result.returncode or not listening(port):
            raise PostgresSetupError("数据库实例启动失败，请查看数据库程序日志或检查端口占用。")
    except (OSError, ValueError, EnvironmentSetupError, subprocess.TimeoutExpired):
        raise PostgresSetupError("数据库程序自动配置未完成，请检查安装、权限或运行日志后重试。") from None
