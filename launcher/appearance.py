"""Local presentation preferences, independent of game and database settings."""
import json
from pathlib import Path

from .core import atomic_json


def preference_path(root):
    root = Path(root).resolve()
    path = root / "runtime/appearance.json"
    path.resolve().relative_to(root)
    return path


def load_dark_mode(root):
    try:
        with preference_path(root).open("r", encoding="utf-8-sig") as source:
            value = json.loads(source.read(1024))
        return isinstance(value, dict) and value.get("mode") == "dark"
    except (OSError, ValueError):
        return False


def save_dark_mode(root, dark):
    atomic_json(preference_path(root), {"mode": "dark" if dark else "light"})
