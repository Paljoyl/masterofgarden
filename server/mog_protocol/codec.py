"""MessagePack values and a reversible JSON representation.

JSON arrays remain arrays: C# [Key(n)] models must not become wire maps.
Documents preserve the original bytes until their value is edited.
"""
from dataclasses import dataclass
import json
import math
import struct
from typing import Any

import msgpack

MAX_BODY_BYTES = 64 * 1024 * 1024
MAX_DEPTH = 128
DOCUMENT_FORMAT = "mog-msgpack-v1"


class CodecError(ValueError):
    """Malformed or unsupported protocol data; never includes body values."""


@dataclass(frozen=True)
class EmptyBody:
    pass


EMPTY = EmptyBody()


@dataclass(frozen=True)
class Extension:
    code: int
    data: bytes


@dataclass
class MapPairs:
    """A map whose duplicate or unhashable keys cannot fit a Python dict."""
    pairs: list[tuple[Any, Any]]


def _map_hook(pairs):
    result = {}
    try:
        for key, value in pairs:
            if key in result:
                return MapPairs(pairs)
            result[key] = value
    except TypeError:
        return MapPairs(pairs)
    return result


def decode(body: bytes) -> Any:
    """Decode one complete message; an empty HTTP body is distinct from nil."""
    if len(body) > MAX_BODY_BYTES:
        raise CodecError("MessagePack body exceeds the size limit")
    if not body:
        return EMPTY
    try:
        value = msgpack.unpackb(body, raw=False, strict_map_key=False,
                               object_pairs_hook=_map_hook,
                               ext_hook=Extension, timestamp=0)
        # Also checks traversal depth consistently with the encoder/JSON view.
        to_jsonable(value)
        return value
    except (ValueError, TypeError, OverflowError, RecursionError) as exc:
        raise CodecError("Invalid MessagePack body: " + type(exc).__name__) from exc


def _guard(depth: int):
    if depth > MAX_DEPTH:
        raise CodecError("Message nesting exceeds the depth limit")


def _extension_bytes(value: Extension) -> bytes:
    if type(value.code) is not int or not -128 <= value.code <= 127:
        raise CodecError("Extension code must be an integer from -128 to 127")
    if not isinstance(value.data, bytes):
        raise CodecError("Extension data must be bytes")
    size = len(value.data)
    fixed = {1: 0xD4, 2: 0xD5, 4: 0xD6, 8: 0xD7, 16: 0xD8}
    if size in fixed:
        header = bytes([fixed[size]])
    elif size <= 0xFF:
        header = b"\xc7" + struct.pack(">B", size)
    elif size <= 0xFFFF:
        header = b"\xc8" + struct.pack(">H", size)
    elif size <= 0xFFFFFFFF:
        header = b"\xc9" + struct.pack(">I", size)
    else:
        raise CodecError("Extension data is too large")
    return header + struct.pack("b", value.code) + value.data


def encode(value: Any, *, single_float: bool = False) -> bytes:
    """Encode native values. MapPairs preserves ordered and duplicate map keys."""
    if isinstance(value, EmptyBody):
        return b""
    packer = msgpack.Packer(use_bin_type=True, use_single_float=single_float)
    output = bytearray()

    def append(data):
        if len(output) + len(data) > MAX_BODY_BYTES:
            raise CodecError("Encoded MessagePack body exceeds the size limit")
        output.extend(data)

    def visit(item, depth):
        _guard(depth)
        if isinstance(item, EmptyBody):
            raise CodecError("Empty HTTP body cannot be nested in a message")
        if isinstance(item, Extension):
            append(_extension_bytes(item))
        elif isinstance(item, MapPairs) or isinstance(item, dict):
            pairs = item.pairs if isinstance(item, MapPairs) else item.items()
            append(packer.pack_map_header(len(item.pairs) if isinstance(item, MapPairs) else len(item)))
            for key, child in pairs:
                visit(key, depth + 1)
                visit(child, depth + 1)
        elif isinstance(item, (list, tuple)) and not isinstance(item, msgpack.ExtType):
            append(packer.pack_array_header(len(item)))
            for child in item:
                visit(child, depth + 1)
        else:
            append(packer.pack(item))

    try:
        visit(value, 0)
        return bytes(output)
    except (ValueError, TypeError, OverflowError, RecursionError) as exc:
        if isinstance(exc, CodecError):
            raise
        raise CodecError("Cannot encode MessagePack value: " + type(exc).__name__) from exc


def to_jsonable(value: Any, _depth: int = 0) -> Any:
    """Preserve binary, extension, timestamps, non-string keys, and infinities."""
    _guard(_depth)
    child = lambda v: to_jsonable(v, _depth + 1)
    if isinstance(value, EmptyBody):
        return {"$msgpack": "empty"}
    if isinstance(value, bytes):
        return {"$msgpack": "binary", "hex": value.hex()}
    if isinstance(value, (Extension, msgpack.ExtType)):
        return {"$msgpack": "extension", "code": value.code, "hex": value.data.hex()}
    if isinstance(value, msgpack.Timestamp):
        return {"$msgpack": "timestamp", "seconds": value.seconds, "nanoseconds": value.nanoseconds}
    if isinstance(value, float) and not math.isfinite(value):
        return {"$msgpack": "float64", "hex": struct.pack(">d", value).hex()}
    if isinstance(value, MapPairs):
        return {"$msgpack": "map", "entries": [[child(k), child(v)] for k, v in value.pairs]}
    if isinstance(value, dict):
        if all(isinstance(k, str) for k in value) and "$msgpack" not in value:
            return {k: child(v) for k, v in value.items()}
        return {"$msgpack": "map", "entries": [[child(k), child(v)] for k, v in value.items()]}
    if isinstance(value, (list, tuple)):
        return [child(v) for v in value]
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    raise CodecError("Unsupported JSON projection type: " + type(value).__name__)


def _hex(value):
    if not isinstance(value, str):
        raise CodecError("Hex payload must be a string")
    try:
        return bytes.fromhex(value)
    except ValueError as exc:
        raise CodecError("Invalid hex payload") from exc


def from_jsonable(value: Any, _depth: int = 0) -> Any:
    _guard(_depth)
    child = lambda v: from_jsonable(v, _depth + 1)
    if isinstance(value, list):
        return [child(v) for v in value]
    if not isinstance(value, dict):
        if value is None or isinstance(value, (str, bool, int, float)):
            return value
        raise CodecError("Invalid JSON value")
    if "$msgpack" not in value:
        return {k: child(v) for k, v in value.items()}
    tag = value["$msgpack"]
    shapes = {"empty": {"$msgpack"}, "binary": {"$msgpack", "hex"},
              "extension": {"$msgpack", "code", "hex"},
              "timestamp": {"$msgpack", "seconds", "nanoseconds"},
              "float64": {"$msgpack", "hex"}, "map": {"$msgpack", "entries"}}
    if not isinstance(tag, str) or tag not in shapes or set(value) != shapes[tag]:
        raise CodecError("Invalid $msgpack tagged value")
    if tag == "empty":
        return EMPTY
    if tag == "binary":
        return _hex(value["hex"])
    if tag == "extension":
        result = Extension(value["code"], _hex(value["hex"]))
        _extension_bytes(result)
        return result
    if tag == "timestamp":
        try:
            return msgpack.Timestamp(value["seconds"], value["nanoseconds"])
        except (TypeError, ValueError) as exc:
            raise CodecError("Invalid MessagePack timestamp") from exc
    if tag == "float64":
        data = _hex(value["hex"])
        if len(data) != 8:
            raise CodecError("Float64 requires exactly eight bytes")
        return struct.unpack(">d", data)[0]
    entries = value["entries"]
    if not isinstance(entries, list) or any(not isinstance(p, list) or len(p) != 2 for p in entries):
        raise CodecError("Map entries must be key/value pairs")
    return MapPairs([(child(k), child(v)) for k, v in entries])


def decode_document(body: bytes) -> dict:
    return {"format": DOCUMENT_FORMAT, "value": to_jsonable(decode(body)),
            "original_hex": body.hex()}


def encode_document(document: dict, *, single_float: bool = False) -> bytes:
    if not isinstance(document, dict) or document.get("format") != DOCUMENT_FORMAT or "value" not in document:
        raise CodecError("Expected a mog-msgpack-v1 document")
    value = from_jsonable(document["value"])
    if "original_hex" in document:
        original = _hex(document["original_hex"])
        # JSON text equality distinguishes True/1 and 1/1.0, unlike Python ==.
        before = json.dumps(to_jsonable(decode(original)), ensure_ascii=True, allow_nan=False)
        after = json.dumps(document["value"], ensure_ascii=True, allow_nan=False)
        if before == after:
            return original
    return encode(value, single_float=single_float)
