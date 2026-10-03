"""Discover registered game endpoints without importing handlers or opening a DB."""
import ast
from pathlib import Path

RESOURCE_ROUTE = "POST /resource/getassetbundlehashes"


def code_routes(root=None):
    root = Path(root) if root is not None else Path(__file__).resolve().parent
    path = root / "local_server/handlers/__init__.py"
    tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
    registry = next((node for node in tree.body
                     if isinstance(node, ast.ClassDef) and node.name == "HandlerRegistry"), None)
    if registry is None:
        raise ValueError("HandlerRegistry not found")
    for node in ast.walk(registry):
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(target, ast.Attribute) and target.attr == "routes"
                   and isinstance(target.value, ast.Name) and target.value.id == "self"
                   for target in node.targets):
            continue
        if not isinstance(node.value, ast.Dict):
            raise ValueError("HandlerRegistry.routes must be a literal endpoint dictionary")
        routes = {RESOURCE_ROUTE}
        for key in node.value.keys:
            if not isinstance(key, ast.Constant) or not isinstance(key.value, str):
                raise ValueError("Registered endpoints must have literal string keys")
            method, separator, endpoint = key.value.partition(" ")
            if not separator or not method.isupper() or not endpoint.startswith("/"):
                raise ValueError("Invalid registered endpoint")
            routes.add(key.value)
        return tuple(sorted(routes))
    raise ValueError("HandlerRegistry.routes not found")
