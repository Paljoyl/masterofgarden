"""Local preparation, bounded diagnostics and owned-process lifecycle."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import http.client
import json
import os
import secrets
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
from typing import Callable

from . import __version__
from .environment import EnvironmentSetupError, ensure_environment, environment_ready, environment_paths, owned_path
from .credentials import CredentialError, database_environment, save_database_password, load_database_password
from .postgres import PostgresSetupError, ensure_postgres, listening as database_listening
from .certificates import CertificateSetupError, ensure_proxy_certificate, proxy_profile
from .processes import owned_pid_groups

ROOT = Path(__file__).resolve().parents[1]
API_PORT = 18180
PROXY_PORT = 18181
WEB_PORT = 18182
FLAGS = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0


class LauncherError(RuntimeError):
    """Public, actionable error containing no raw subprocess output."""


@dataclass(frozen=True)
class Settings:
    game_exe: str = ""
    proxy_exe: str = ""
    dbname: str = "MogLocalOpenSource"
    dbuser: str = "postgres"
    dbport: int = 5432
    api_port: int = API_PORT
    proxy_port: int = PROXY_PORT
    web_port: int = WEB_PORT

    @property
    def service_ports(self):
        return (self.api_port, self.proxy_port, self.web_port)

    @property
    def ports(self):
        return (*self.service_ports, self.dbport)

    def validate(self):
        for key in ("game_exe", "proxy_exe", "dbname", "dbuser"):
            if not isinstance(getattr(self, key), str):
                raise LauncherError(f"配置字段 {key} 必须是文本。")
        for key, title in (("api_port", "API 服务"), ("proxy_port", "本地接入"),
                           ("web_port", "接入管理"), ("dbport", "数据库")):
            port = getattr(self, key)
            if type(port) is not int or not 1 <= port <= 65535:
                raise LauncherError(title + "端口必须在 1–65535 之间。")
        if len(set(self.ports)) != len(self.ports):
            raise LauncherError("API、接入、管理和数据库端口不能重复，请分别设置。")
        if not self.dbname.strip() or not self.dbuser.strip():
            raise LauncherError("数据库名称和用户名不能为空。")
        if self.dbname.casefold() == "ｍaster of garden".casefold():
            raise LauncherError("请使用独立数据库，例如 MogLocalOpenSource，避免连接调试存档。")
        for key in ("game_exe", "proxy_exe"):
            value = getattr(self, key)
            if value and not Path(value).is_absolute():
                raise LauncherError(f"请为 {key} 选择完整路径。")
        if self.game_exe and Path(self.game_exe).name.casefold() != "masterofgarden.exe":
            raise LauncherError("请选择 MasterofGarden.exe 游戏入口。")
        if self.proxy_exe and Path(self.proxy_exe).name.casefold() != "mitmweb.exe":
            raise LauncherError("请选择 mitmweb.exe 本地接入工具。")
        return self


@dataclass(frozen=True)
class Check:
    key: str
    title: str
    state: str
    detail: str
    remedy: str = ""


def atomic_json(path: Path, value: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as out:
            temporary = Path(out.name)
            json.dump(value, out, ensure_ascii=False, indent=2)
            out.write("\n")
        os.replace(temporary, path)
    finally:
        if temporary and temporary.exists():
            temporary.unlink()


def load_settings(root: Path = ROOT) -> Settings:
    path = root / "runtime/settings.json"
    if not path.exists():
        return Settings()
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        if isinstance(data, dict):
            data.pop("resource_dir", None)
            data.pop("server_python", None)
        if not isinstance(data, dict) or set(data) - set(Settings.__dataclass_fields__):
            raise LauncherError("启动器配置格式错误；请检查 runtime/settings.json。")
        return Settings(**data).validate()
    except (OSError, ValueError, TypeError) as exc:
        raise LauncherError("启动器配置无法读取；请检查 runtime/settings.json。") from exc


def selected_paths(settings: Settings, root: Path = ROOT) -> dict[str, Path]:
    return {
        "game": Path(settings.game_exe) if settings.game_exe else root / "client/MasterofGarden.exe",
        "proxy": Path(settings.proxy_exe) if settings.proxy_exe else root / "runtime/tools/mitmproxy/mitmweb.exe",
        "python": environment_paths(root, "server")[1],
        "server": root / "server/server.py",
        "bridge": root / "server/mitm_local.py",
        "schema": root / "server/mog_protocol/schemas.json",
        "config": root / "runtime/server.config.json",
    }


def server_config(settings: Settings) -> dict:
    settings.validate()
    return {
        "listen": {"host": "127.0.0.1", "port": settings.api_port},
        "upstream": "https://tw-prd-green-api.shadow-garden-mog.tw",
        "api_hosts": ["tw-prd-green-api.shadow-garden-mog.tw"],
        "database": {"driver": "postgresql", "host": "127.0.0.1", "port": settings.dbport,
                     "dbname": settings.dbname, "user": settings.dbuser,
                     "password_env": "MOG_DB_PASSWORD"},
        "captures": [], "overrides": "overrides", "mode": "local",
        "timeout_seconds": 20, "upstream_proxy": "direct", "forward_prefixes": [],
        "routes": {}, "max_body_bytes": 67108864,
    }


def prepare(settings: Settings, root: Path = ROOT, progress=lambda text: None) -> list[str]:
    """Prepare private configuration and the automatically managed server Python."""
    settings.validate()
    config = root / "runtime/server.config.json"
    desired = server_config(settings)
    # Protect existing manual changes instead of silently overwriting them.
    if config.exists():
        try:
            previous = json.loads(config.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError) as exc:
            raise LauncherError("已有服务配置无法读取。请先在本机检查，不会自动覆盖。") from exc
        if previous != desired:
            raise LauncherError("已有服务配置与设置不同。请先在设置页备份并更新服务配置。")
    try:
        ensure_environment(root, "server", progress)
    except EnvironmentSetupError as exc:
        raise LauncherError(str(exc)) from exc
    for directory in ("runtime/logs", "runtime/proxy-profile", "runtime/overrides", "runtime/reports"):
        (root / directory).mkdir(parents=True, exist_ok=True)
    atomic_json(root / "runtime/settings.json", asdict(settings))
    if not config.exists():
        atomic_json(config, desired)
    return ["已保存本机路径和独立数据库设置。", "已准备本地模式配置；抓包列表和转发规则为空。",
            "Python 与依赖已自动准备。首次本地登录自动建立新存档，无需玩家响应或抓包。"]


def initialize_database(settings: Settings, root: Path = ROOT, *, password=None, progress=lambda text: None):
    """Explicitly create the selected database if absent and apply migrations."""
    settings.validate()
    paths = selected_paths(settings, root)
    try:
        if json.loads(paths["config"].read_text(encoding="utf-8-sig")) != server_config(settings):
            raise LauncherError("数据库设置与服务配置不一致，请先完成一键配置。")
        if not paths["python"].is_file():
            raise LauncherError("请先完成 Python 环境配置。")
        progress("正在连接 PostgreSQL，创建目标数据库并应用迁移…")
        log = owned_path(root, root / "runtime/logs/database-setup.log")
        log.parent.mkdir(parents=True, exist_ok=True)
        with log.open("ab") as output:
            result = subprocess.run([str(paths["python"]), "-B", "-m", "PostgreSQL.database_cli",
                                     "--config", str(paths["config"]), "--diagnostic-root", str(root),
                                     "init", "--create-database"],
                                    cwd=root / "server", stdout=output, stderr=output,
                                    timeout=180, creationflags=FLAGS, env=database_environment(root, password))
        if result.returncode:
            raise LauncherError("数据库初始化失败，请查看运行日志中的「数据库初始化」，并检查连接信息、密码和用户建库权限。")
        check = database_readiness(settings, root, password=password)
        if check.state != "pass":
            raise LauncherError("数据库初始化后的检查未通过：" + check.detail)
        progress("数据库已就绪；首次登录会自动创建本地账号。")
    except CredentialError as exc:
        raise LauncherError(str(exc)) from None
    except subprocess.TimeoutExpired:
        raise LauncherError("数据库初始化超时，请检查 PostgreSQL 后重试；已执行的迁移不会重复应用。") from None
    except EnvironmentSetupError as exc:
        raise LauncherError(str(exc)) from None
    except (OSError, ValueError):
        raise LauncherError("数据库初始化无法执行，请检查本机配置并重新完成一键配置。") from None


def configure_all(settings: Settings, root: Path = ROOT, *, password="", progress=lambda text: None,
                  on_password_saved=None):
    """User-confirmed GUI setup, including credential storage and database init."""
    settings.validate()
    # A new project-owned instance can choose its own password; an existing service cannot.
    try:
        if not password:
            password = load_database_password(root) or os.environ.get("MOG_DB_PASSWORD", "")
            if not password and not database_listening(settings.dbport) and not (root / "runtime/postgres/PG_VERSION").exists():
                password = secrets.token_urlsafe(24)
                progress("已自动生成本项目数据库密码，将加密保存在本机。")
        save_database_password(root, password)
    except CredentialError as exc:
        raise LauncherError(str(exc)) from None
    if on_password_saved is not None:
        # A separate callback keeps the credential out of progress text and logs.
        on_password_saved(password)
    config = root / "runtime/server.config.json"
    if config.exists():
        try:
            same = json.loads(config.read_text(encoding="utf-8-sig")) == server_config(settings)
        except ValueError:
            same = False
        if not same:
            progress("正在备份并更新服务配置…")
            replace_server_config(settings, root)
    lines = prepare(settings, root, progress)
    try:
        ensure_postgres(root, settings.dbport, settings.dbuser, password, progress)
    except PostgresSetupError as exc:
        raise LauncherError(str(exc)) from None
    initialize_database(settings, root, password=password, progress=progress)
    return lines + ["一键配置完成：数据库与 Python 环境已就绪。"]


def replace_server_config(settings: Settings, root: Path = ROOT):
    desired = server_config(settings)
    path = root / "runtime/server.config.json"
    if path.exists():
        # Unique local backup; its contents never enter feedback reports.
        backup = path.with_name(f"server.config.{time.time_ns()}.backup.json")
        backup.write_bytes(path.read_bytes())
    atomic_json(path, desired)
    atomic_json(root / "runtime/settings.json", asdict(settings))


def port_open(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.25):
            return True
    except OSError:
        return False


def local_health(port: int = API_PORT) -> bool:
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=1)
    try:
        connection.request("GET", "/_local/health")
        response = connection.getresponse()
        value = json.loads(response.read(65536))
        return response.status == 200 and isinstance(value, dict) and value.get("ok") is True and value.get("service") == "mog-local"
    except (OSError, ValueError, http.client.HTTPException):
        return False
    finally:
        connection.close()



def database_readiness(settings: Settings, root: Path, *, password=None) -> Check:
    paths = selected_paths(settings, root)
    remedy = "在设置页填写连接信息和密码，然后点击「一键完成配置」。"
    try:
        result = subprocess.run([str(paths["python"]), "-B", "-m", "PostgreSQL.readiness", "--config", str(paths["config"])],
            cwd=root / "server", stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=10,
            creationflags=FLAGS, env=database_environment(root, password))
        value = json.loads(result.stdout.decode("utf-8"))
        reason = value.get("reason")
        messages = {
            "standalone_ready": "数据库所需结构与版本已齐全；首次登录会自动创建本地账号，无需抓包。",
            "database_not_initialized": "独立数据库尚未初始化。",
            "migrations_pending": "数据库需要应用当前版本的迁移。",
            "database_schema_incomplete": "数据库所需结构缺失或不兼容。",
            "schema_contract_outdated": "服务端结构检查清单与当前 SQL 版本不一致，请更新完整的服务端文件。",
            "migration_checksum_mismatch": "已执行的迁移与当前代码不一致，请恢复对应版本后检查。",
            "database_version_newer_than_code": "数据库版本比当前服务端代码新，请使用匹配的代码版本。",
            "database_connection_failed": "无法连接独立数据库，请检查 PostgreSQL、数据库名称和密码。",
        }
        passed = result.returncode == 0 and value.get("state") == "pass" and reason == "standalone_ready"
        detail = messages.get(reason, "数据库就绪检查未通过。")
        if passed:
            detail = f"所需结构检查通过：{value.get('tables', 0)} 张表、{value.get('columns', 0)} 个字段；已有数据库可直接使用，首次登录自动创建本地账号。"
        elif reason == "migrations_pending":
            detail += f" 待应用 {value.get('pending', 0)} 项，请点击「一键完成配置」。"
        for key, label in (("missing_tables", "缺少表"), ("missing_columns", "缺少字段"),
                           ("incompatible_columns", "字段类型或空值要求不符"), ("missing_keys", "缺少主键／唯一键")):
            entries = value.get(key, [])
            if isinstance(entries, list) and entries:
                names = [entry for entry in entries if isinstance(entry, str)]
                detail += f" {label}（{len(names)}）：" + "、".join(names[:4]) + ("等。" if len(names) > 4 else "。")
        if reason == "database_schema_incomplete":
            remedy = "请恢复完整数据库备份，或在新数据库重新完成配置；保留已有库和迁移记录。"
        elif reason == "schema_contract_outdated":
            remedy = "重新取得与当前 SQL 匹配的服务端文件及结构检查清单。"
        return Check("data.readiness", "独立数据库与本地账号", "pass" if passed else "error",
                     detail, "" if passed else remedy)
    except CredentialError as exc:
        return Check("data.readiness", "独立数据库与本地账号", "error", str(exc), remedy)
    except (OSError, ValueError, AttributeError, subprocess.TimeoutExpired):
        return Check("data.readiness", "独立数据库与本地账号", "error", "无法完成数据库检查，请先配置 Python 与服务端。", remedy)


def inspect(settings: Settings, root: Path = ROOT, *, network: bool = True,
            owned: set[str] | None = None, password=None, owned_processes=None) -> list[Check]:
    """Probe loopback only. Presence checks are not completeness guarantees."""
    settings.validate()
    paths = selected_paths(settings, root)
    checks = [Check("launcher.python", "启动器运行环境", "pass" if sys.version_info >= (3, 10) else "error",
                    "Python 3.10 或更新版本。", "安装 Python 3.10+。" if sys.version_info < (3, 10) else "")]
    for key, title, remedy in (
        ("game", "游戏入口", "在设置页选择合法取得的 MasterofGarden.exe。"),
        ("server", "公开版服务端", "服务端文件缺失，请重新取得完整项目。"),
        ("bridge", "本地接入桥接", "本地接入桥接缺失，请重新取得完整项目。"),
        ("schema", "协议定义", "协议定义缺失，请重新取得完整项目。"),
        ("proxy", "本地接入工具", "安装 mitmproxy 后在设置页选择 mitmweb.exe。"),
        ("python", "服务端 Python", "点击「一键配置」自动创建 Python 环境并安装依赖。"),
        ("config", "本机服务配置", "选择路径后点击「一键配置」。"),
    ):
        present = paths[key].is_file()
        checks.append(Check(key, title, "pass" if present else "error",
                            "所需文件已找到。" if present else "所需文件未找到。", "" if present else remedy))
    if paths["config"].is_file():
        try:
            config_ok = json.loads(paths["config"].read_text(encoding="utf-8-sig")) == server_config(settings)
        except (OSError, ValueError):
            config_ok = False
        checks.append(Check("config.policy", "配置一致性", "pass" if config_ok else "error",
                            "本地模式配置与设置一致。" if config_ok else "配置与设置不一致或无法读取。",
                            "在设置页备份并更新服务配置。"))
    if paths["python"].is_file():
        dependencies_ok = environment_ready(root, "server")
        checks.append(Check("server.dependencies", "服务端依赖", "pass" if dependencies_ok else "error",
                            "独立环境、依赖版本与自动配置标记检查通过。" if dependencies_ok else "Python 依赖未准备完成或验证未通过。",
                            "点击「一键配置」自动安装或修复 Python 依赖。"))
    if network:
        owned = owned or set()
        listeners, groups, ownership_failed = None, {}, False
        if owned_processes is not None:
            from .status import tcp_listeners, LOCAL_ADDRESSES
            try:
                listeners = tcp_listeners()
                groups = owned_pid_groups(owned_processes, {entry.pid for entry in listeners
                                          if entry.port in settings.service_ports})
            except OSError:
                ownership_failed = True
        for tag, port, title in (("server", settings.api_port, "API 端口"), ("proxy", settings.proxy_port, "内部代理端口"),
                                 ("proxy", settings.web_port, "内部就绪端口")):
            if ownership_failed:
                checks.append(Check(f"port.{port}", title, "error", "无法确认端口占用归属。", "请等待状态自动更新后重试。"))
                continue
            entries = [entry for entry in listeners if entry.port == port and entry.address in LOCAL_ADDRESSES] if listeners is not None else None
            occupied = bool(entries) if entries is not None else port_open(port)
            ours = all(entry.pid in groups.get(tag, set()) for entry in entries) if entries is not None else tag in owned
            state = "pass" if not occupied or ours else "error"
            checks.append(Check(f"port.{port}", title, state,
                                "本次启动器管理的进程正在使用。" if occupied and ours else
                                "端口已被其他实例占用。" if occupied else "端口可用。",
                                "在开始游戏页查看占用进程，可确认关闭后重试。" if state == "error" else ""))
        database = port_open(settings.dbport)
        checks.append(Check("database.listener", "本地数据库入口", "pass" if database else "error",
                            "本地数据库端口已有服务监听；认证与迁移结果见独立数据库检查。" if database else "本地数据库端口没有监听。",
                            "" if database else "确认 PostgreSQL 已运行，在设置页填写连接信息后点击「一键完成配置」。"))
    else:
        checks.append(Check("network", "运行连接检查", "warn", "离线检查未连接端口或数据库。"))
    if network:
        checks.append(database_readiness(settings, root, password=password))
    else:
        checks.append(Check("data.readiness", "独立数据库与本地账号", "warn",
                            "离线检查不连接数据库；首次本地登录自动创建新存档。",
                            "运行完整环境检查以验证数据库结构。"))
    return checks


def feedback_report(checks: list[Check]) -> str:
    """An allowlist of check IDs/statuses; paths, logs and DB identity are excluded."""
    lines = ["# MasterofGarden 启动器问题反馈", "", f"启动器版本：{__version__}",
             f"Python：{sys.version_info.major}.{sys.version_info.minor}", f"平台：{sys.platform}",
             f"生成时间（UTC）：{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}", "",
             "## 问题描述", "请填写你执行的步骤、期望结果和实际结果。", "", "## 检查状态", ""]
    lines.extend(f"- {check.key}: {check.state}" for check in checks)
    lines.extend(["", "此摘要未包含本机路径、用户名、数据库名称、密码、令牌、原始日志、请求正文或抓包。",
                  "提交前请检查自己填写的内容；反馈入口尚未配置，请暂时手动分享此摘要。", ""])
    return "\n".join(lines)


def game_already_running() -> bool:
    if os.name != "nt":
        return False
    try:
        result = subprocess.run(["tasklist.exe", "/FI", "IMAGENAME eq MasterofGarden.exe", "/FO", "CSV", "/NH"],
                                capture_output=True, timeout=5, creationflags=FLAGS)
        if result.returncode:
            raise LauncherError("无法确认是否已有游戏运行。请关闭已有游戏后重试。")
        return b'"masterofgarden.exe"' in result.stdout.lower()
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise LauncherError("无法检查已有游戏进程。请关闭已有游戏后重试。") from exc


class Runtime:
    """Retain Popen handles and stop only processes started by this instance."""

    def __init__(self, root: Path = ROOT):
        self.root = root
        self.children: dict[str, subprocess.Popen] = {}
        self.started_at: dict[str, float] = {}
        self.stopped_tags: set[str] = set()
        self.running_ports = None

    def owned(self) -> set[str]:
        return {tag for tag, child in self.children.items() if child.poll() is None}

    def _spawn(self, tag: str, args: list[str], cwd: Path, *, env=None):
        logs = self.root / "runtime/logs"
        logs.mkdir(parents=True, exist_ok=True)
        with (logs / f"{tag}.log").open("ab") as output:
            child = subprocess.Popen(args, cwd=cwd, stdout=output, stderr=output, creationflags=FLAGS,
                                     env=dict(os.environ, PYTHONUTF8="1") if env is None else env, close_fds=True)
        self.children[tag] = child
        self.started_at[tag] = time.monotonic()
        self.stopped_tags.discard(tag)
        return child

    @staticmethod
    def _wait(child, ready: Callable[[], bool], error: str):
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            if child.poll() is not None:
                raise LauncherError(error + "：进程已退出，请在本机查看日志。")
            if ready():
                return
            time.sleep(.25)
        raise LauncherError(error + "：等待就绪超时。")

    def start(self, settings: Settings, progress: Callable[[str], None], *, password=None):
        settings.validate()
        if os.name != "nt":
            raise LauncherError("游戏接入目前仅支持 Windows。")
        initial = self.owned()
        if initial and self.running_ports is not None and self.running_ports != settings.ports:
            raise LauncherError("请先停止本次启动，再更改端口。")
        if "game" in initial:
            raise LauncherError("本次启动的游戏仍在运行；请先停止，再重新启动。")
        if game_already_running():
            raise LauncherError("检测到已有游戏，请从原窗口退出后再启动，避免影响调试会话。")
        roots = {tag: child.pid for tag, child in tuple(self.children.items()) if tag in initial}
        checks = inspect(settings, self.root, owned=initial, password=password, owned_processes=roots)
        if any(check.state == "error" for check in checks):
            raise LauncherError("环境存在缺失项，请先到「环境准备」查看并处理。")
        paths = selected_paths(settings, self.root)
        self.running_ports = settings.ports
        try:
            profile = proxy_profile(self.root)
            if "server" not in initial:
                progress("正在启动独立本地服务…")
                child = self._spawn("server", [str(paths["python"]), "-u", str(paths["server"]),
                                                "--config", str(paths["config"])], self.root / "server",
                                    env=database_environment(self.root, password))
                self._wait(child, lambda: local_health(settings.api_port), "本地服务未就绪")
            elif not local_health(settings.api_port):
                raise LauncherError("本次本地服务未通过健康检查。请停止后重新启动。")
            if "proxy" not in initial:
                progress("正在准备仅本机的游戏接入…")
                child = self._spawn("proxy", [str(paths["proxy"]), "--mode", "local:MasterofGarden",
                    "--listen-host", "127.0.0.1", "--listen-port", str(settings.proxy_port),
                    "--web-host", "127.0.0.1", "--web-port", str(settings.web_port),
                    "--set", "web_open_browser=false", "--set", "connection_strategy=lazy",
                    "--set", f"confdir={profile}",
                    "--ignore-hosts", r"^(.+\.)?googleapis\.com:443$", "-s", str(paths["bridge"]),
                    "--set", f"mog_config={paths['config']}"], self.root)
                self._wait(child, lambda: port_open(settings.web_port), "本地接入未就绪")
            ensure_proxy_certificate(self.root, progress)
            progress("正在启动游戏…")
            child = self._spawn("game", [str(paths["game"])], paths["game"].parent)
            time.sleep(.5)
            if child.poll() is not None:
                raise LauncherError("游戏启动后立即退出，请查看运行日志。")
            progress("游戏进程已启动。")
        except CertificateSetupError as exc:
            self.stop(set(self.owned()) - initial)
            raise LauncherError(str(exc)) from None
        except Exception:
            self.stop(set(self.owned()) - initial)
            raise

    def stop(self, tags: set[str] | None = None):
        targets = set(self.children) if tags is None else tags
        for tag in ("game", "proxy", "server"):
            if tag not in targets:
                continue
            child = self.children.get(tag)
            if child is not None and child.poll() is None:
                self.stopped_tags.add(tag)
                child.terminate()
                try:
                    child.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait(timeout=5)
