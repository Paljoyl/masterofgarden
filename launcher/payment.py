"""Reversible TW PC local-payment SDK shim, adapted from the read-only development tool."""
import argparse
import hashlib
import os
from pathlib import Path
import shutil
import struct
import tempfile

from .core import ROOT, LauncherError, load_settings, selected_paths
from .processes import process_inventory

# Keep the development tool's verified client contract; never guess a new offset.
RVA = 0x12B6FE0  # SsgSdkController.Purchase(ShopPaymentMaster): UniTask<bool>
ORIGINAL_SHA256 = "129748009eb3fa6fe3208ba5359291ab45e78d63d06d53c210e44ea46089e3fb"
PATCHED_SHA256 = "02e3a9c82098b89e22a2a38c8e1ceab4ea7b4ad04bb39529ee281e45b093edd7"
ORIGINAL = bytes.fromhex("48895c24084889742410574881ec90000000")
# Windows x64 sret: rcx points to UniTask<bool>, result at byte 8.
PATCH = bytes.fromhex("0f57c00f1101c64108014889c8c3")


class PaymentPatchError(LauncherError):
    pass


def digest(path):
    result = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def offset(path):
    with path.open("rb") as source:
        if source.read(2) != b"MZ":
            raise PaymentPatchError("客户端 DLL 不是受支持的 Windows 文件。")
        source.seek(0x3c)
        source.seek(struct.unpack("<I", source.read(4))[0])
        if source.read(4) != b"PE\0\0":
            raise PaymentPatchError("客户端 DLL 的 PE 文件头无效。")
        coff = source.read(20)
        machine, sections = struct.unpack_from("<HH", coff)
        if machine != 0x8664:
            raise PaymentPatchError("本地支付补丁仅支持已核对的 x64 TW 客户端。")
        source.seek(struct.unpack_from("<H", coff, 16)[0], 1)
        for _ in range(sections):
            section = source.read(40)
            virtual_size, address, raw_size, raw_offset = struct.unpack_from("<IIII", section, 8)
            if address <= RVA < address + min(virtual_size, raw_size):
                return raw_offset + RVA - address
    raise PaymentPatchError("未找到已核对的支付函数，本次未修改 DLL。")


def require_game_closed():
    try:
        processes = process_inventory()
    except OSError:
        raise PaymentPatchError("无法确认游戏是否已退出，请检查进程权限后重试。") from None
    if any(info.name.casefold() == "masterofgarden.exe" for info in processes.values()):
        raise PaymentPatchError("请先退出所有 MasterofGarden 游戏窗口，再修改或恢复 DLL。")


def client_files(game_exe, root):
    game = Path(game_exe)
    if not game.is_absolute() or game.name.casefold() != "masterofgarden.exe" or not game.is_file():
        raise PaymentPatchError("请在设置页选择存在的 MasterofGarden.exe 游戏入口。")
    game = game.resolve()
    debug_root = (Path(root).resolve().parent / "Ｍaster of Garden").resolve()
    if game.is_relative_to(debug_root):
        raise PaymentPatchError("原开发项目仅供只读参考，请选择当前项目或独立客户端副本。")
    dll = game.parent / "GameAssembly.dll"
    backup = dll.with_name("GameAssembly.dll.before-local-payment.bak")
    for path in (dll, backup):
        if path.is_symlink() or path.resolve().parent != game.parent:
            raise PaymentPatchError("DLL 或备份指向其他目录，请选择独立客户端副本。")
    if not dll.is_file():
        raise PaymentPatchError("游戏入口旁缺少 GameAssembly.dll，请使用完整客户端。")
    return dll, backup


def patch_client(game_exe, root=ROOT, *, restore=False, progress=lambda text: None):
    """Validate the full image, preserve one original backup, then replace atomically."""
    temporary = None
    incomplete_backup = None
    try:
        dll, backup = client_files(game_exe, root)
        require_game_closed()
        progress("正在核对客户端 DLL：" + str(dll))
        current_hash = digest(dll)
        expected = ORIGINAL_SHA256 if restore else PATCHED_SHA256
        if current_hash == expected:
            return "客户端 DLL 已恢复，无需重复操作。" if restore else "本地支付 DLL 补丁已启用，无需重复修改。"
        required = PATCHED_SHA256 if restore else ORIGINAL_SHA256
        if current_hash != required:
            raise PaymentPatchError("客户端版本与已核对的补丁不一致，本次未修改 DLL。")
        position = offset(dll)
        with dll.open("rb") as source:
            source.seek(position)
            expected_bytes = PATCH if restore else ORIGINAL
            if source.read(len(expected_bytes)) != expected_bytes:
                raise PaymentPatchError("客户端支付函数与预期不一致，本次未修改 DLL。")
        if backup.exists():
            if not backup.is_file() or digest(backup) != ORIGINAL_SHA256:
                raise PaymentPatchError("已有备份不是对应的原始 DLL，保留该文件并选择独立客户端副本。")
        elif restore:
            raise PaymentPatchError("未找到原始 DLL 备份，无法恢复。")
        else:
            progress("正在保存原始 DLL 备份…")
            # Exclusive creation prevents a concurrent invocation from overwriting a backup.
            try:
                with backup.open("xb") as target:
                    incomplete_backup = backup
                    with dll.open("rb") as source:
                        shutil.copyfileobj(source, target, 1024 * 1024)
                    target.flush()
                    os.fsync(target.fileno())
            except FileExistsError:
                pass
            if digest(backup) != ORIGINAL_SHA256:
                raise PaymentPatchError("原始 DLL 备份未完成或文件已变化，本次未替换 DLL。")
            incomplete_backup = None
        descriptor, name = tempfile.mkstemp(prefix=".mog-payment-", suffix=".dll", dir=dll.parent)
        os.close(descriptor)
        temporary = Path(name)
        shutil.copy2(backup if restore else dll, temporary)
        if not restore:
            with temporary.open("r+b") as target:
                target.seek(position)
                target.write(PATCH)
                target.flush()
                os.fsync(target.fileno())
        if digest(temporary) != expected:
            raise PaymentPatchError("生成的 DLL 未通过摘要核对，本次未替换客户端文件。")
        require_game_closed()
        if digest(dll) != current_hash:
            raise PaymentPatchError("客户端 DLL 在操作期间发生变化，请重试；本次未替换文件。")
        os.replace(temporary, dll)
        progress("原始 DLL 备份：" + str(backup))
        return "客户端 DLL 已恢复，玩家存档保持不变。" if restore else "本地支付 DLL 补丁已启用，请通过启动器启动本地游戏。"
    except PermissionError:
        raise PaymentPatchError("本次未替换 DLL，请退出游戏并检查客户端目录权限后重试。") from None
    except (OSError, ValueError, struct.error):
        raise PaymentPatchError("客户端文件无法读取或操作未完成，请检查完整客户端和目录权限后重试。") from None
    finally:
        for path in (temporary, incomplete_backup):
            if path is not None:
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    pass


def main():
    parser = argparse.ArgumentParser(description="修改或恢复本地支付客户端 DLL")
    parser.add_argument("--restore", action="store_true")
    parser.add_argument("--game-exe", type=Path, help="覆盖已保存的游戏入口路径")
    args = parser.parse_args()
    try:
        game = args.game_exe or selected_paths(load_settings(), ROOT)["game"]
        print(patch_client(game, restore=args.restore, progress=lambda text: print(text, flush=True)))
        return 0
    except LauncherError as exc:
        print(str(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
