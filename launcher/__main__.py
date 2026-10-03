import argparse
import json
from dataclasses import asdict
from .core import LauncherError, inspect, load_settings
from .environment import EnvironmentSetupError, ensure_environment
from .core import ROOT


def main():
    parser = argparse.ArgumentParser(description="MasterofGarden local launcher")
    parser.add_argument("--check", action="store_true", help="检查本机环境，不启动游戏")
    parser.add_argument("--offline", action="store_true", help="检查时跳过本地端口探测")
    parser.add_argument("--check-ui", action="store_true", help="验证界面依赖，不打开窗口")
    parser.add_argument("--setup-python", action="store_true", help="自动配置服务端 Python 与依赖")
    parser.add_argument("--setup-launcher", action="store_true", help="自动配置缺失的启动器界面依赖")
    args = parser.parse_args()
    if args.setup_python or args.setup_launcher:
        try:
            ensure_environment(ROOT, "server" if args.setup_python else "launcher", lambda text: print(text, flush=True))
        except (EnvironmentSetupError, OSError) as exc:
            print(str(exc) if isinstance(exc, EnvironmentSetupError) else "自动配置无法写入，请检查目录权限后重试。")
            return 2
        return 0
    if args.check:
        try:
            checks = inspect(load_settings(), network=not args.offline)
        except LauncherError as exc:
            print(str(exc))
            return 2
        print(json.dumps([asdict(check) for check in checks], ensure_ascii=False, indent=2))
        return int(any(check.state == "error" for check in checks))
    if args.check_ui:
        try:
            from .qt import BINDING
        except ImportError:
            print("界面依赖尚未安装。请双击 MasterofGarden.cmd 自动准备界面依赖。")
            return 2
        print("界面依赖可用：" + BINDING)
        return 0
    try:
        from .app import main as gui_main
    except ImportError:
        print("界面依赖尚未安装。请双击 MasterofGarden.cmd 自动准备界面依赖。")
        return 2
    return gui_main()


if __name__ == "__main__":
    raise SystemExit(main())
