"""Per-project database credentials protected by the current Windows user."""
import ctypes
from ctypes import wintypes
import os
from pathlib import Path
import tempfile


class CredentialError(RuntimeError):
    """Actionable errors that never include credential contents."""


def _crypt(data: bytes, *, decrypt=False) -> bytes:
    if os.name != "nt":
        raise CredentialError("保存数据库密码需要 Windows；也可使用 MOG_DB_PASSWORD 环境变量。")

    class Blob(ctypes.Structure):
        _fields_ = [("size", wintypes.DWORD), ("data", ctypes.POINTER(ctypes.c_ubyte))]

    buffer = ctypes.create_string_buffer(data)
    source = Blob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte)))
    target = Blob()
    crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)
    function = crypt32.CryptUnprotectData if decrypt else crypt32.CryptProtectData
    function.argtypes = [ctypes.POINTER(Blob), ctypes.c_void_p, ctypes.POINTER(Blob),
                         ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(Blob)]
    function.restype = wintypes.BOOL
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.LocalFree.argtypes = [ctypes.c_void_p]
    kernel32.LocalFree.restype = ctypes.c_void_p
    try:
        # UI_FORBIDDEN, without LOCAL_MACHINE: protection belongs to this user.
        if not function(ctypes.byref(source), None, None, None, None, 1, ctypes.byref(target)):
            raise CredentialError("数据库密码无法解密，请重新填写并保存。" if decrypt else "数据库密码加密失败，请重试。")
        return ctypes.string_at(target.data, target.size)
    finally:
        ctypes.memset(buffer, 0, ctypes.sizeof(buffer))
        if target.data:
            ctypes.memset(target.data, 0, target.size)
            kernel32.LocalFree(target.data)


def _password_path(root: Path) -> Path:
    path = Path(root) / "runtime/database-password.dpapi"
    try:
        path.resolve().relative_to(Path(root).resolve())
    except ValueError:
        raise CredentialError("密码文件必须位于本项目运行目录中。") from None
    return path


def load_database_password(root: Path) -> str:
    try:
        data = _password_path(root).read_bytes()
    except FileNotFoundError:
        return ""
    except OSError:
        raise CredentialError("数据库密码文件无法读取，请检查运行目录权限。") from None
    try:
        return _crypt(data, decrypt=True).decode("utf-8")
    except UnicodeError:
        raise CredentialError("数据库密码文件无效，请重新填写并保存。") from None


def save_database_password(root: Path, password: str):
    if "\x00" in password:
        raise CredentialError("数据库密码不能包含空字符。")
    path = _password_path(root)
    temporary = None
    try:
        if not password:
            path.unlink(missing_ok=True)
            return
        data = _crypt(password.encode("utf-8"))
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as output:
            temporary = Path(output.name)
            output.write(data)
        os.replace(temporary, path)
    except OSError:
        raise CredentialError("数据库密码保存失败，请检查运行目录权限。") from None
    finally:
        if temporary and temporary.exists():
            temporary.unlink()


def database_environment(root: Path, password=None) -> dict[str, str]:
    """Explicit input > saved credential > inherited environment; never mutate it."""
    environment = dict(os.environ, PYTHONUTF8="1")
    if password is None:
        password = load_database_password(root)
    if password:
        if "\x00" in password:
            raise CredentialError("数据库密码不能包含空字符。")
        environment["MOG_DB_PASSWORD"] = password
    return environment
