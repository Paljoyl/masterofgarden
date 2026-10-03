"""Automatically prepare project-owned Python environments; never use global pip."""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time

FLAGS = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
COMPONENTS = {"server": ("server/requirements.txt", "import msgpack, psycopg"),
              "launcher": ("launcher/requirements-launcher.txt", "from PySide6.QtWidgets import QApplication")}


class EnvironmentSetupError(RuntimeError):
    pass


def owned_path(root, path):
    root, path = Path(root).resolve(), Path(path).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise EnvironmentSetupError("运行目录指向项目之外，请检查目录链接后重试。") from exc
    return path


def environment_paths(root, component):
    if component not in COMPONENTS:
        raise EnvironmentSetupError("不支持的 Python 环境类型。")
    directory = owned_path(root, Path(root) / f"runtime/{component}-env")
    python = directory / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    return directory, python, directory / "ready.json"


def requirements_info(root, component):
    try:
        filename = COMPONENTS[component][0]
        content = (Path(root) / filename).read_bytes()
    except (OSError, KeyError) as exc:
        raise EnvironmentSetupError("Python 依赖清单缺失，请检查启动器文件是否齐全。") from exc
    text = content.decode("utf-8-sig")
    pins = re.findall(r"^([A-Za-z0-9_.-]+)(?:\[[^\]]+\])?==([^\s;#]+)\s*$", text, re.MULTILINE)
    return hashlib.sha256(content).hexdigest(), pins


def probe(python, directory, component, pins):
    if not python.is_file():
        return False
    code = ("import sys,pathlib,json,importlib.metadata as m; "
            "assert (3,10) <= sys.version_info[:2] < (3,15); "
            "assert sys.maxsize > 2**32; "
            "assert pathlib.Path(sys.prefix).resolve() == pathlib.Path(sys.argv[1]).resolve(); "
            + COMPONENTS[component][1] + "; "
            "assert all(m.version(name)==version for name,version in json.loads(sys.argv[2]))")
    try:
        result = subprocess.run([str(python), "-I", "-c", code, str(directory), json.dumps(pins)],
                                capture_output=True, timeout=15, creationflags=FLAGS)
        return result.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def interpreter_ready(python, directory):
    """Separate a broken interpreter from missing or outdated dependencies."""
    if not python.is_file():
        return False
    code = ("import sys,pathlib,venv,ensurepip; "
            "assert (3,10) <= sys.version_info[:2] < (3,15); "
            "assert sys.maxsize > 2**32; "
            "assert pathlib.Path(sys.prefix).resolve() == pathlib.Path(sys.argv[1]).resolve()")
    try:
        result = subprocess.run([str(python), "-I", "-c", code, str(directory)],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                timeout=15, creationflags=FLAGS)
        return result.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def environment_ready(root, component="server"):
    try:
        directory, python, marker = environment_paths(root, component)
        fingerprint, pins = requirements_info(root, component)
        value = json.loads(marker.read_text(encoding="utf-8"))
        return value.get("requirements_sha256") == fingerprint and probe(python, directory, component, pins)
    except (OSError, ValueError, EnvironmentSetupError, AttributeError):
        return False


@contextmanager
def setup_lock(root):
    filename = owned_path(root, Path(root) / "runtime/python-setup.lock")
    filename.parent.mkdir(parents=True, exist_ok=True)
    with filename.open("a+b") as lock:
        if filename.stat().st_size == 0:
            lock.write(b"0")
            lock.flush()
        lock.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise EnvironmentSetupError("另一窗口正在配置 Python，请等待完成后重试。") from exc
        try:
            yield
        finally:
            lock.seek(0)
            if os.name == "nt":
                msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def run_step(arguments, log, message, timeout):
    with log.open("ab") as output:
        try:
            result = subprocess.run([str(argument) for argument in arguments], stdout=output,
                                    stderr=output, timeout=timeout, creationflags=FLAGS,
                                    env=dict(os.environ, PYTHONUTF8="1", PYTHONDONTWRITEBYTECODE="1"))
        except subprocess.TimeoutExpired as exc:
            raise EnvironmentSetupError(message + "超时，请检查网络后重试；详细日志在本机运行目录。") from exc
        except OSError as exc:
            raise EnvironmentSetupError(message + "未能启动，请检查磁盘与目录权限后重试。") from exc
        if result.returncode:
            raise EnvironmentSetupError(message + "失败，请查看本机 runtime/logs 中的配置日志，再重试。")


def ensure_environment(root, component="server", progress=lambda text: None):
    root = Path(root).resolve()
    directory, python, marker = environment_paths(root, component)
    fingerprint, pins = requirements_info(root, component)
    label = "服务端" if component == "server" else "启动器"
    with setup_lock(root):
        if environment_ready(root, component):
            progress(label + " Python 已就绪，无需重复安装。")
            return python
        logs = owned_path(root, root / "runtime/logs")
        logs.mkdir(parents=True, exist_ok=True)
        log = logs / f"python-{component}-setup.log"
        if not interpreter_ready(python, directory):
            # Preserve a failed environment, but never move linked directories or
            # the interpreter currently running this configuration operation.
            if directory != root / f"runtime/{component}-env":
                raise EnvironmentSetupError("Python 环境目录使用了目录链接，已保留文件；请使用项目自身的运行目录后重试。")
            if Path(sys.prefix).resolve() == directory:
                raise EnvironmentSetupError("当前使用的 Python 环境已失效。请关闭启动器，再双击 MasterofGarden.cmd，使用其他已安装的 Python 重建。")
            if directory.exists():
                if not directory.is_dir():
                    raise EnvironmentSetupError("Python 环境路径不是目录，已保留现有文件；请检查后重试。")
                backup = owned_path(root, directory.with_name(f"{directory.name}.broken-{time.time_ns()}"))
                try:
                    directory.rename(backup)
                except OSError as exc:
                    raise EnvironmentSetupError("失效 Python 环境无法备份，请停止使用该环境的程序并检查目录权限后重试。") from exc
                progress("已保留失效的" + label + " Python 环境：" + str(backup.relative_to(root)))
            progress("正在自动创建" + label + "独立 Python 环境…")
            base = Path(getattr(sys, "_base_executable", sys.executable))
            run_step([base, "-I", "-m", "venv", directory], log, "创建 Python 环境", 120)
        # A failed installation must never leave a success marker.
        if marker.exists():
            marker.unlink()
        progress("正在准备" + label + "的包管理工具…")
        run_step([python, "-I", "-m", "ensurepip"], log, "准备 Python 包管理工具", 120)
        progress("正在安装" + label + "依赖，首次配置需要联网…")
        run_step([python, "-I", "-m", "pip", "--isolated", "--disable-pip-version-check", "install",
                  "--no-input", "--only-binary=:all:", "--index-url", "https://pypi.org/simple",
                  "--timeout", "30", "--retries", "2", "-r", root / COMPONENTS[component][0]],
                 log, "安装 Python 依赖", 600)
        progress("正在验证" + label + " Python 与依赖版本…")
        if not probe(python, directory, component, pins):
            raise EnvironmentSetupError("Python 依赖验证未通过，请再次运行一键配置；本机日志可用于定位问题。")
        run_step([python, "-I", "-m", "pip", "check"], log, "检查 Python 依赖兼容性", 30)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=directory, delete=False) as out:
                temporary = Path(out.name)
                json.dump({"requirements_sha256": fingerprint}, out)
            os.replace(temporary, marker)
        finally:
            if temporary and temporary.exists():
                temporary.unlink()
        progress(label + " Python 已自动配置完成。")
        return python
