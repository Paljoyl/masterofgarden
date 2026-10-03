"""Read-only Windows process ancestry for launcher-owned worker recognition."""
import ctypes
from ctypes import wintypes
from dataclasses import dataclass
import os


@dataclass(frozen=True)
class ProcessInfo:
    name: str
    parent: int


def process_inventory():
    if os.name != "nt":
        raise OSError("Windows process API required")

    class Entry(ctypes.Structure):
        _fields_ = [("size", wintypes.DWORD), ("usage", wintypes.DWORD), ("pid", wintypes.DWORD),
                    ("heap", ctypes.c_size_t), ("module", wintypes.DWORD), ("threads", wintypes.DWORD),
                    ("parent", wintypes.DWORD), ("priority", wintypes.LONG), ("flags", wintypes.DWORD),
                    ("name", wintypes.WCHAR * 260)]

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    kernel.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL
    for function in (kernel.Process32FirstW, kernel.Process32NextW):
        function.argtypes = [wintypes.HANDLE, ctypes.POINTER(Entry)]
        function.restype = wintypes.BOOL
    handle = kernel.CreateToolhelp32Snapshot(2, 0)
    if handle == ctypes.c_void_p(-1).value:
        raise OSError("Process snapshot unavailable")
    result = {}
    try:
        entry = Entry()
        entry.size = ctypes.sizeof(Entry)
        available = kernel.Process32FirstW(handle, ctypes.byref(entry))
        while available:
            result[entry.pid] = ProcessInfo(entry.name, entry.parent)
            available = kernel.Process32NextW(handle, ctypes.byref(entry))
        if ctypes.get_last_error() != 18:
            raise OSError("Process snapshot incomplete")
    finally:
        kernel.CloseHandle(handle)
    return result


def process_creation_time(pid):
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL
    kernel.GetProcessTimes.argtypes = [wintypes.HANDLE, *[ctypes.POINTER(wintypes.FILETIME)] * 4]
    kernel.GetProcessTimes.restype = wintypes.BOOL
    handle = kernel.OpenProcess(0x1000, False, pid)
    if not handle:
        return None
    try:
        times = [wintypes.FILETIME() for _ in range(4)]
        if not kernel.GetProcessTimes(handle, *[ctypes.byref(value) for value in times]):
            return None
        return (times[0].dwHighDateTime << 32) | times[0].dwLowDateTime
    finally:
        kernel.CloseHandle(handle)


def owned_pid_groups(roots, candidates, *, inventory=None, creation_time=None):
    """Recognize live roots and verified descendants, rejecting recycled parent PIDs."""
    groups = {tag: {pid} for tag, pid in roots.items()}
    if not roots:
        return groups
    inventory = process_inventory() if inventory is None else inventory
    creation_time = process_creation_time if creation_time is None else creation_time
    owners = {pid: tag for tag, pid in roots.items()}
    times = {}

    def born(pid):
        if pid not in times:
            times[pid] = creation_time(pid)
        return times[pid]

    for candidate in set(candidates) - set(owners):
        pid, visited = candidate, set()
        for _ in range(64):
            if pid in visited or pid not in inventory:
                break
            visited.add(pid)
            parent = inventory[pid].parent
            child_time, parent_time = born(pid), born(parent) if parent else None
            if child_time is None or parent_time is None or parent_time > child_time:
                break
            if parent in owners:
                groups[owners[parent]].add(candidate)
                break
            pid = parent
    return groups


def managed_process_tag(children, pid):
    roots = {tag: child.pid for tag, child in tuple(children.items()) if child.poll() is None}
    direct = next((tag for tag, root in roots.items() if root == pid), None)
    if direct:
        return direct
    groups = owned_pid_groups(roots, [pid])
    return next((tag for tag, pids in groups.items() if pid in pids), None)
