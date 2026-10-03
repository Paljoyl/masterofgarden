"""Explicit, confirmed port-owner shutdown with native process identity checks."""
from contextlib import contextmanager
import ctypes
from ctypes import wintypes
from dataclasses import dataclass
import os
from pathlib import Path
import subprocess

from .core import LauncherError, FLAGS
from .status import tcp_listeners
from .processes import managed_process_tag


@dataclass(frozen=True)
class ProcessTarget:
    port: int
    pid: int
    executable: str
    created: int

    @property
    def name(self):
        return Path(self.executable).name


PROTECTED = {"system", "registry", "smss.exe", "csrss.exe", "wininit.exe", "services.exe",
             "lsass.exe", "winlogon.exe", "svchost.exe"}


def _kernel():
    if os.name != "nt":
        raise OSError("Windows process API required")
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    signatures = {
        "OpenProcess": ([wintypes.DWORD, wintypes.BOOL, wintypes.DWORD], wintypes.HANDLE),
        "CloseHandle": ([wintypes.HANDLE], wintypes.BOOL),
        "GetProcessTimes": ([wintypes.HANDLE, *[ctypes.POINTER(wintypes.FILETIME)] * 4], wintypes.BOOL),
        "QueryFullProcessImageNameW": ([wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR,
                                       ctypes.POINTER(wintypes.DWORD)], wintypes.BOOL),
        "IsProcessCritical": ([wintypes.HANDLE, ctypes.POINTER(wintypes.BOOL)], wintypes.BOOL),
        "TerminateProcess": ([wintypes.HANDLE, wintypes.UINT], wintypes.BOOL),
        "WaitForSingleObject": ([wintypes.HANDLE, wintypes.DWORD], wintypes.DWORD),
    }
    for name, (arguments, result) in signatures.items():
        function = getattr(kernel, name)
        function.argtypes, function.restype = arguments, result
    return kernel


@contextmanager
def _process(pid, *, terminate=False):
    if pid in (0, 4, os.getpid()) or pid < 0:
        raise LauncherError("此系统进程或启动器自身不能在这里关闭。")
    kernel = _kernel()
    handle = kernel.OpenProcess(0x1000 | 0x100000 | (1 if terminate else 0), False, pid)
    if not handle:
        raise LauncherError("进程已退出或当前用户没有关闭权限，请刷新状态或从原程序退出。")
    try:
        critical = wintypes.BOOL()
        if not kernel.IsProcessCritical(handle, ctypes.byref(critical)) or critical.value:
            raise LauncherError("不能关闭系统关键进程，请从对应程序或系统服务管理器处理。")
        yield kernel, handle
    finally:
        kernel.CloseHandle(handle)


def _identity(kernel, handle):
    times = [wintypes.FILETIME() for _ in range(4)]
    path = ctypes.create_unicode_buffer(32768)
    size = wintypes.DWORD(len(path))
    if not kernel.GetProcessTimes(handle, *[ctypes.byref(value) for value in times]) or not kernel.QueryFullProcessImageNameW(
            handle, 0, path, ctypes.byref(size)):
        raise LauncherError("无法确认进程身份，请刷新状态后重试。")
    if Path(path.value).name.casefold() in PROTECTED:
        raise LauncherError("不能从启动器关闭系统服务进程，请从系统服务管理器处理。")
    return path.value, (times[0].dwHighDateTime << 32) | times[0].dwLowDateTime


def _verify_listener(port, pid):
    if not any(entry.port == port and entry.pid == pid for entry in tcp_listeners()):
        raise LauncherError("端口占用已变化，本次没有关闭程序，请刷新后重试。")


def prepare_target(port, pid):
    """Capture identity immediately before showing the confirmation dialog."""
    try:
        with _process(pid) as (kernel, handle):
            executable, created = _identity(kernel, handle)
            _verify_listener(port, pid)
            return ProcessTarget(port, pid, executable, created)
    except OSError:
        raise LauncherError("无法读取端口占用或进程权限，请刷新状态后重试。") from None


def close_port_process(target, runtime, progress=lambda text: None):
    """Close one confirmed PID; hold its handle so PID reuse cannot redirect termination."""
    database = target.name.casefold() == "postgres.exe"
    try:
        with _process(target.pid, terminate=not database) as (kernel, handle):
            if _identity(kernel, handle) != (target.executable, target.created):
                raise LauncherError("进程身份已变化，本次没有关闭程序，请刷新后重试。")
            _verify_listener(target.port, target.pid)
            progress(f"正在关闭 {target.name} · PID {target.pid} · 端口 {target.port}…")
            tag = managed_process_tag(runtime.children, target.pid)
            if database:
                # PostgreSQL's Windows signal implementation requests clean fast shutdown.
                # Never fall back to TerminateProcess for a database server.
                command = Path(target.executable).with_name("pg_ctl.exe")
                if not command.is_file():
                    raise LauncherError("未找到此数据库配套的 pg_ctl，请从数据库服务管理器正常停止。")
                runtime.stop()
                result = subprocess.run([str(command), "kill", "INT", str(target.pid)],
                                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                        creationflags=FLAGS, timeout=5)
                if result.returncode:
                    raise LauncherError("数据库正常停止请求失败，请检查权限或从数据库服务管理器停止。")
            elif tag:
                tags = {"game", "proxy", "server"} if tag == "server" else {"game", "proxy"} if tag == "proxy" else {tag}
                runtime.stop(tags)
            elif not kernel.TerminateProcess(handle, 1):
                raise LauncherError("无法关闭此进程，请检查权限或从原程序退出。")
            if kernel.WaitForSingleObject(handle, 30000 if database else 5000) != 0:
                raise LauncherError("已请求停止，进程尚未退出；请查看状态，稍后再试。")
        progress(f"已关闭 {target.name} · PID {target.pid}，正在刷新端口状态。")
    except (OSError, subprocess.TimeoutExpired):
        raise LauncherError("关闭程序未完成，请刷新状态并检查权限。") from None
