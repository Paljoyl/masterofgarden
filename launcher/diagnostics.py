"""Local exception diagnostics without driver messages, arguments or frame locals."""
from datetime import datetime
from pathlib import Path
import re
import traceback


def record_exception(root, error, *, context="后台操作", filename="launcher-errors.log"):
    """Best-effort logging must never hide the original operation failure."""
    if filename not in {"launcher-errors.log", "database-setup.log"}:
        return False
    try:
        root = Path(root).resolve()
        path = root / "runtime/logs" / filename
        path.resolve().relative_to(root)
        lines = [f"[{datetime.now().astimezone().isoformat(timespec='seconds')}] {context}"]
        seen = set()
        while error is not None and id(error) not in seen:
            seen.add(id(error))
            lines.append("异常类型：" + type(error).__name__)
            state = getattr(error, "sqlstate", None)
            if isinstance(state, str) and re.fullmatch(r"[0-9A-Z]{5}", state):
                lines.append("SQLSTATE：" + state)
            migration = getattr(error, "migration", None)
            if isinstance(migration, str) and re.fullmatch(r"[0-9]+_[A-Za-z0-9_]+\.sql", migration):
                lines.append("迁移文件：" + migration)
            for frame, number in traceback.walk_tb(error.__traceback__):
                source = Path(frame.f_code.co_filename)
                try:
                    source = source.resolve().relative_to(root)
                except ValueError:
                    source = Path(source.name)
                lines.append(f"  {source}:{number} · {frame.f_code.co_name}")
            error = error.__cause__ or error.__context__
        lines.append("日志省略异常原始消息、连接串、命令参数及局部变量。\n")
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as output:
            output.write("\n".join(lines) + "\n")
        return True
    except Exception:
        return False
