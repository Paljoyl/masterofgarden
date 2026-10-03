"""Read-only process and TCP-listener snapshots for the live launcher panel."""
import ctypes
from ctypes import wintypes
from dataclasses import dataclass, field
import os
from pathlib import Path
import socket
import struct

from .core import API_PORT, PROXY_PORT, WEB_PORT, local_health
from .processes import process_inventory, owned_pid_groups

LOCAL_ADDRESSES = ("127.0.0.1", "::1", "0.0.0.0", "::")


@dataclass(frozen=True)
class Listener:
    port: int
    address: str
    pid: int


@dataclass(frozen=True)
class ProcessState:
    pid: int
    exit_code: int | None
    elapsed: float = 0
    stopped: bool = False


@dataclass(frozen=True)
class StatusItem:
    title: str
    state: str
    text: str
    detail: str = ""


@dataclass(frozen=True)
class StatusSnapshot:
    components: dict[str, StatusItem]
    ports: list[StatusItem]
    owned_running: bool
    game_running: bool
    conflicts: bool
    unavailable: bool = False
    port_processes: dict[int, dict[int, str]] = field(default_factory=dict)


def parse_tcp_table(data: bytes, family: int) -> list[Listener]:
    if len(data) < 4:
        raise OSError("Invalid TCP table")
    count = struct.unpack_from("=I", data)[0]
    row_size = 24 if family == socket.AF_INET else 56
    if 4 + count * row_size > len(data):
        raise OSError("Incomplete TCP table")
    result = []
    for index in range(count):
        offset = 4 + index * row_size
        if family == socket.AF_INET:
            state, address, port, _, _, pid = struct.unpack_from("=6I", data, offset)
            address = socket.inet_ntoa(struct.pack("=I", address))
        else:
            address, scope, port, _, _, _, state, pid = struct.unpack_from("=16sII16sIIII", data, offset)
            address = socket.inet_ntop(socket.AF_INET6, address)
            if scope:
                address += f"%{scope}"
        if state == 2:  # MIB_TCP_STATE_LISTEN; established sockets are not port owners.
            result.append(Listener(socket.ntohs(port & 0xffff), address, pid))
    return result


def tcp_listeners() -> list[Listener]:
    if os.name != "nt":
        raise OSError("Windows status API required")
    function = ctypes.WinDLL("iphlpapi").GetExtendedTcpTable
    function.argtypes = [ctypes.c_void_p, ctypes.POINTER(wintypes.DWORD), wintypes.BOOL,
                         wintypes.ULONG, ctypes.c_int, wintypes.ULONG]
    function.restype = wintypes.DWORD
    result = []
    for family in (socket.AF_INET, socket.AF_INET6):
        size = wintypes.DWORD()
        code = function(None, ctypes.byref(size), False, family, 3, 0)
        for _ in range(3):
            if code not in (0, 122) or not 4 <= size.value <= 16 * 1024 * 1024:
                raise OSError("TCP listener query unavailable")
            buffer = ctypes.create_string_buffer(size.value)
            code = function(buffer, ctypes.byref(size), False, family, 3, 0)
            if code == 0:
                result.extend(parse_tcp_table(buffer.raw[:size.value], family))
                break
        else:
            raise OSError("TCP listener query changed repeatedly")
    return result


def process_names() -> dict[int, str]:
    """Read executable basenames only; never inspect command lines or environments."""
    return {pid: info.name for pid, info in process_inventory().items()}


def managed_database_pid(root):
    path = Path(root) / "runtime/postgres/postmaster.pid"
    try:
        path.resolve().relative_to(Path(root).resolve())
        with path.open(encoding="utf-8") as source:
            pid = int(source.readline().strip())
        return pid if pid > 0 else None
    except (OSError, ValueError):
        return None


def build_snapshot(dbport, processes, listeners, names, *, database_pid=None, healthy=False, owned_pids=None,
                   api_port=API_PORT, proxy_port=PROXY_PORT, web_port=WEB_PORT):
    """Classify observed listeners by their actual PID, not just a live child handle."""
    unavailable = listeners is None
    processes_unavailable = names is None
    listeners = listeners or []
    names = names or {}
    active = {tag: process.pid for tag, process in processes.items() if process.exit_code is None}
    owned_pids = owned_pids or {tag: {pid} for tag, pid in active.items()}
    components = {}
    for tag, title in (("server", "服务端"), ("proxy", "本地接入"), ("game", "游戏")):
        process = processes.get(tag)
        if process is None:
            components[tag] = StatusItem(title, "warn", "未启动")
        elif process.exit_code is not None:
            text = "已停止" if process.stopped else "已退出" if process.exit_code == 0 else "异常退出"
            components[tag] = StatusItem(title, "error" if process.exit_code and not process.stopped else "warn",
                                         text, f"PID {process.pid} · 退出码 {process.exit_code}")
        else:
            seconds = int(process.elapsed)
            detail = f"PID {process.pid} · {seconds // 60:02d}:{seconds % 60:02d}"
            workers = owned_pids.get(tag, set()) - {process.pid}
            if workers:
                detail += " · 工作进程 PID " + ", ".join(map(str, sorted(workers)))
            text, state = "运行中", "pass"
            if tag == "server" and not unavailable:
                text, state = ("服务就绪", "pass") if healthy else ("等待服务就绪", "warn")
            components[tag] = StatusItem(title, state, text, detail)
    external_games = [pid for pid, name in names.items() if name.casefold() == "masterofgarden.exe" and pid not in owned_pids.get("game", set())]
    if external_games and "game" not in active:
        components["game"] = StatusItem("游戏", "warn", "其他实例运行中", "PID " + ", ".join(map(str, external_games)))
    elif processes_unavailable and "game" not in active:
        components["game"] = StatusItem("游戏", "warn", "监测暂不可用", "无法确认其他游戏实例")
    ports = []
    conflicts = False
    for port, title, tag in ((api_port, "API 服务", "server"), (proxy_port, "内部接入", "proxy"),
                             (web_port, "接入管理", "proxy"), (dbport, "数据库", "database")):
        entries = [listener for listener in listeners if listener.port == port]
        expected = {database_pid} if tag == "database" else owned_pids.get(tag, set())
        local = [entry for entry in entries if entry.address in LOCAL_ADDRESSES]
        foreign = [entry for entry in local if entry.pid not in expected]
        if unavailable:
            text, state, detail = "无法读取", "warn", "端口监测暂不可用"
        elif not entries:
            text, state, detail = "空闲", "pass", "没有 TCP 监听"
        else:
            detail = "\n".join(sorted({f"{names.get(entry.pid, '未知进程')} · PID {entry.pid} · {entry.address}" for entry in entries}))
            if tag == "database":
                text, state = ("本项目数据库", "pass") if local and not foreign else (
                    "已有服务监听", "pass") if local else ("其他地址监听", "warn")
            elif foreign:
                text, state = "其他程序占用", "error"
                conflicts = True
            elif local:
                text, state = "本次启动占用", "pass"
            else:
                text, state = "其他地址监听", "warn"
        ports.append(StatusItem(f"{title} · {port}", state, text, detail))
    db_entries = [listener for listener in listeners if listener.port == dbport and listener.address in LOCAL_ADDRESSES]
    db_pids = sorted({entry.pid for entry in db_entries})
    components["database"] = StatusItem("数据库", "warn" if unavailable or not db_entries else "pass",
        "无法读取" if unavailable else "未监听" if not db_entries else "本项目实例" if database_pid in db_pids else "已有服务监听",
        "PID " + ", ".join(map(str, db_pids)) if db_pids else "监听状态不代表认证通过")
    targets = {port: {entry.pid: names.get(entry.pid, "未知进程") for entry in listeners if entry.port == port}
               for port in (api_port, proxy_port, web_port, dbport)}
    return StatusSnapshot(components, ports, bool(active), "game" in active or bool(external_games), conflicts,
                          unavailable or processes_unavailable, targets)


def inspect_status(root, dbport, processes, *, api_port=API_PORT, proxy_port=PROXY_PORT, web_port=WEB_PORT):
    try:
        listeners = tcp_listeners()
    except OSError:
        listeners = None
    try:
        inventory = process_inventory()
        names = {pid: info.name for pid, info in inventory.items()}
    except OSError:
        inventory, names = {}, None
    roots = {tag: process.pid for tag, process in processes.items() if process.exit_code is None}
    candidates = {entry.pid for entry in (listeners or []) if entry.port in (api_port, proxy_port, web_port)}
    candidates.update(pid for pid, name in (names or {}).items() if name.casefold() == "masterofgarden.exe")
    owned = owned_pid_groups(roots, candidates, inventory=inventory)
    healthy = bool(listeners and any(
        entry.port == api_port and entry.pid in owned.get("server", set()) and entry.address in LOCAL_ADDRESSES
        for entry in listeners) and local_health(api_port))
    return build_snapshot(dbport, processes, listeners, names, database_pid=managed_database_pid(root), healthy=healthy,
                          owned_pids=owned, api_port=api_port, proxy_port=proxy_port, web_port=web_port)
