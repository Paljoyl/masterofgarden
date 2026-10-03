"""Integer-key C# model schemas derived from Il2CppDumper's dump.cs."""
from pathlib import Path
import json
import re

from .codec import CodecError, from_jsonable, to_jsonable

DEFAULT_SCHEMAS = Path(__file__).with_name("schemas.json")


def extract_schemas(dump_path: Path) -> dict:
    models = {}
    endpoints = {}
    namespace = ""
    current = None
    messagepack_object = False
    pending_key = None
    declaration = re.compile(r"^(?:public|internal) (?:sealed |abstract |static )?(class|struct|interface) (\w+)(?:\s*:\s*([^/]+))? // TypeDefIndex:")
    member = re.compile(r"\s*public (.+?) (\w+)(?:\s+\{\s*get;|;)")
    method = re.compile(r"UniTask<([^>]+)> ((?:Post|Get)\w+)Async\((.*)\)")

    def finish():
        if current and current["model"]:
            previous = models.get(current["name"])
            if previous and previous["namespace"] != current["namespace"]:
                raise CodecError("Ambiguous model name in schema source: " + current["name"])
            models[current["name"]] = {
                "namespace": current["namespace"], "base": current["base"],
                "fields": sorted(current["fields"], key=lambda f: f["index"])}

    with Path(dump_path).open(encoding="utf-8-sig") as source:
        for line in source:
            if line.startswith("// Namespace:"):
                finish()
                current = None
                namespace = line.partition(":")[2].strip()
                messagepack_object = False
                pending_key = None
            if line.startswith("[MessagePackObject(False)]"):
                messagepack_object = True
            match = declaration.match(line)
            if match:
                finish()
                kind, name, bases = match.groups()
                current = {"name": name, "namespace": namespace,
                           "base": (bases or "").split(",")[0].strip(), "fields": [],
                           "model": messagepack_object and namespace.startswith("CaravanWa.Shared"),
                           "interface": kind == "interface" and namespace == "CaravanWa.Network.WebApi" and name.endswith("Api")}
                messagepack_object = False
                pending_key = None
            if current is None:
                continue
            key = re.search(r"\[Key\((\d+)\)\]", line)
            if key:
                pending_key = int(key[1])
            elif pending_key is not None:
                prop = member.match(line)
                if prop and current["model"]:
                    current["fields"].append({"index": pending_key, "name": prop[2], "type": prop[1]})
                    pending_key = None
            if current["interface"]:
                match = method.search(line)
                if match:
                    response, name, arguments = match.groups()
                    verb = "POST" if name.startswith("Post") else "GET"
                    suffix = name[4:] if verb == "POST" else name[3:]
                    group = current["name"][1:-3].lower()
                    request = re.search(r"(?:^|,\s*)([\w<>., ]+) request(?:,|$)", arguments)
                    endpoints[f"{verb} /{group}/{suffix.lower()}"] = {
                        "request": request[1].strip() if request else None,
                        "response": response, "interface": current["name"],
                        "method": name + "Async"}
    finish()
    # Include inherited indexed fields, where a known model is the base class.
    def inherited(name, stack):
        if name in stack:
            raise CodecError("Cyclic model inheritance in schema source")
        model = models[name]
        fields = inherited(model["base"], stack | {name}) if model["base"] in models else []
        indices = {f["index"]: f for f in fields}
        for field in model["fields"]:
            if field["index"] in indices and field != indices[field["index"]]:
                raise CodecError("Conflicting indexed fields in schema: " + name)
            indices[field["index"]] = field
        return sorted(indices.values(), key=lambda f: f["index"])
    flattened = {name: inherited(name, set()) for name in models}
    for name, fields in flattened.items():
        models[name]["fields"] = fields
    return {"format": "mog-schema-v1", "source": "Il2CppDumper dump.cs",
            "models": models, "endpoints": endpoints}


def _generic(type_name):
    match = re.fullmatch(r"([\w.]+)<(.*)>", type_name)
    if not match:
        return None, []
    parts, start, depth = [], 0, 0
    for i, ch in enumerate(match[2]):
        if ch == "<":
            depth += 1
        elif ch == ">":
            depth -= 1
        elif ch == "," and depth == 0:
            parts.append(match[2][start:i].strip())
            start = i + 1
    parts.append(match[2][start:].strip())
    return match[1].split(".")[-1], parts


class SchemaRegistry:
    def __init__(self, path: Path = DEFAULT_SCHEMAS):
        with Path(path).open(encoding="utf-8-sig") as source:
            self.data = json.load(source)
        if self.data.get("format") != "mog-schema-v1":
            raise CodecError("Unsupported schema format")
        self.models = self.data["models"]

    def endpoint(self, method: str, path: str):
        return self.data["endpoints"].get(method.upper() + " " + path)

    def named(self, value, type_name: str, depth: int = 0):
        """Render typed arrays as named records; retain length and extra fields."""
        if depth > 100:
            raise CodecError("Model nesting exceeds the depth limit")
        if value is None:
            return None
        container, args = _generic(type_name)
        if container in ("Nullable",) and args:
            return self.named(value, args[0], depth + 1)
        if (container in ("List", "IReadOnlyList", "IReadOnlyCollection", "IEnumerable", "HashSet") and args) or type_name.endswith("[]"):
            child_type = args[0] if args else type_name[:-2]
            if isinstance(value, list):
                return [self.named(item, child_type, depth + 1) for item in value]
        model = self.models.get(type_name)
        if model is None or not isinstance(value, list):
            return to_jsonable(value)
        fields = {f["index"]: f for f in model["fields"]}
        named = {}
        unknown = {}
        for index, item in enumerate(value):
            if index in fields:
                field = fields[index]
                named[field["name"]] = self.named(item, field["type"], depth + 1)
            else:
                unknown[str(index)] = to_jsonable(item)
        result = {"$model": type_name, "length": len(value), "fields": named}
        if unknown:
            result["unknown"] = unknown
        return result

    def positional(self, value, type_name: str, depth: int = 0):
        """Reverse a named view into the original positional layout."""
        if depth > 100:
            raise CodecError("Model nesting exceeds the depth limit")
        if value is None:
            return None
        container, args = _generic(type_name)
        if container == "Nullable" and args:
            return self.positional(value, args[0], depth + 1)
        if (container in ("List", "IReadOnlyList", "IReadOnlyCollection", "IEnumerable", "HashSet") and args) or type_name.endswith("[]"):
            child_type = args[0] if args else type_name[:-2]
            if isinstance(value, list):
                return [self.positional(item, child_type, depth + 1) for item in value]
        model = self.models.get(type_name)
        if model is not None and isinstance(value, dict) and "$model" not in value and "$msgpack" not in value:
            raise CodecError("Named model requires its $model tag")
        if model is None or not isinstance(value, dict) or "$model" not in value:
            return from_jsonable(value)
        if value["$model"] != type_name or set(value) - {"$model", "length", "fields", "unknown"}:
            raise CodecError("Named model does not match the requested schema")
        length = value.get("length")
        if type(length) is not int or not 0 <= length <= 100000:
            raise CodecError("Invalid named model length")
        given = value.get("fields")
        unknown = value.get("unknown", {})
        if not isinstance(given, dict) or not isinstance(unknown, dict):
            raise CodecError("Named fields and unknown indices must be objects")
        fields = {f["name"]: f for f in model["fields"]}
        if set(given) - set(fields):
            raise CodecError("Unknown named field for model " + type_name)
        if any(f["index"] < length and name not in given for name, f in fields.items()):
            raise CodecError("Named model is missing a field; use an explicit null to clear it")
        result = [None] * length
        occupied = set()
        for name, item in given.items():
            field = fields[name]
            index = field["index"]
            if index >= length:
                raise CodecError("Named field index is beyond model length")
            result[index] = self.positional(item, field["type"], depth + 1)
            occupied.add(index)
        known_indices = {f["index"] for f in fields.values()}
        for index_text, item in unknown.items():
            if not index_text.isdigit() or str(int(index_text)) != index_text:
                raise CodecError("Invalid unknown model field index")
            index = int(index_text)
            if index >= length or index in occupied or index in known_indices:
                raise CodecError("Unknown model field index conflicts with schema")
            result[index] = from_jsonable(item)
        return result
