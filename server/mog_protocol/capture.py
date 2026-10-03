"""Offline reader for mitmproxy 12 typed-netstring captures; no replay/network."""
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
import gzip
import zlib
from typing import BinaryIO, Iterator

from .codec import CodecError, MAX_BODY_BYTES

MAX_FLOW_BYTES = 128 * 1024 * 1024
MAX_DEPTH = 128


class CaptureError(ValueError):
    pass


def _read_value(stream: BinaryIO, depth: int = 0):
    if depth > MAX_DEPTH:
        raise CaptureError("Capture nesting exceeds the depth limit")
    length = bytearray()
    while True:
        ch = stream.read(1)
        if ch == b":" and length:
            break
        if not ch:
            if not length:
                raise EOFError
            raise CaptureError("Truncated capture length prefix")
        if not ch.isdigit() or len(length) >= 12:
            raise CaptureError("Invalid capture length prefix")
        length.extend(ch)
    size = int(length)
    if size > MAX_FLOW_BYTES:
        raise CaptureError("Capture record exceeds the size limit")
    raw = stream.read(size)
    tag = stream.read(1)
    if len(raw) != size or not tag:
        raise CaptureError("Truncated capture record (stop the writer before exporting)")
    if tag == b",":
        return raw
    if tag == b";":
        return raw.decode("utf-8")
    if tag == b"~" and not raw:
        return None
    if tag == b"!" and raw in (b"true", b"false"):
        return raw == b"true"
    if tag in (b"#", b"^"):
        try:
            return int(raw) if tag == b"#" else float(raw)
        except ValueError as exc:
            raise CaptureError("Invalid capture number") from exc
    if tag in (b"]", b"}"):
        nested = BytesIO(raw)
        values = []
        while nested.tell() < size:
            values.append(_read_value(nested, depth + 1))
        if tag == b"]":
            return values
        if len(values) % 2:
            raise CaptureError("Capture map has an unmatched key")
        try:
            return dict(zip(values[::2], values[1::2]))
        except TypeError as exc:
            raise CaptureError("Invalid capture map key") from exc
    raise CaptureError("Unsupported capture type tag")


def read_flows(path: Path) -> Iterator[dict]:
    with Path(path).open("rb") as stream:
        index = 0
        while True:
            offset = stream.tell()
            try:
                flow = _read_value(stream)
            except EOFError:
                return
            except (CaptureError, UnicodeError, RecursionError) as exc:
                raise CaptureError(f"Invalid capture at record {index}, byte {offset}: {type(exc).__name__}") from exc
            if not isinstance(flow, dict):
                raise CaptureError(f"Capture record {index} is not a flow map")
            yield flow
            index += 1


def field(data: dict, name: str, default=None):
    return data.get(name, data.get(name.encode(), default))


def _text(value):
    return value.decode("utf-8", errors="replace") if isinstance(value, bytes) else str(value or "")


def headers(message: dict) -> dict[str, str]:
    return {_text(k).lower(): _text(v) for k, v in field(message, "headers", [])}


def _bounded_decompress(body: bytes, encoding: str) -> bytes:
    if encoding == "gzip":
        with gzip.GzipFile(fileobj=BytesIO(body)) as source:
            result = source.read(MAX_BODY_BYTES + 1)
    else:
        def inflate(wbits):
            decoder = zlib.decompressobj(wbits)
            result = decoder.decompress(body, MAX_BODY_BYTES + 1)
            if len(result) > MAX_BODY_BYTES or decoder.unconsumed_tail:
                raise CodecError("Decompressed body exceeds the size limit")
            if not decoder.eof or decoder.unused_data:
                raise CodecError("Invalid deflate body")
            return result
        try:
            result = inflate(zlib.MAX_WBITS)
        except zlib.error:
            result = inflate(-zlib.MAX_WBITS)
    if len(result) > MAX_BODY_BYTES:
        raise CodecError("Decompressed body exceeds the size limit")
    return result


def message_body(message: dict) -> bytes:
    body = field(message, "content")
    if body is None:
        raise CodecError("Capture message body is missing")
    if not isinstance(body, bytes) or len(body) > MAX_BODY_BYTES:
        raise CodecError("Invalid capture body or body exceeds the size limit")
    encoding = headers(message).get("content-encoding", "").strip().lower()
    if encoding in ("", "identity"):
        return body
    if encoding not in ("gzip", "deflate"):
        raise CodecError("Unsupported HTTP content encoding: " + encoding)
    try:
        return _bounded_decompress(body, encoding)
    except (OSError, EOFError, zlib.error) as exc:
        raise CodecError("Invalid compressed HTTP body") from exc


@dataclass
class CapturedMessage:
    flow_index: int
    host: str
    path: str
    method: str
    direction: str
    status: int | None
    body: bytes


def iter_api_messages(path: Path) -> Iterator[CapturedMessage]:
    for index, flow in enumerate(read_flows(path)):
        if _text(field(flow, "type")) != "http":
            continue
        request = field(flow, "request")
        if not isinstance(request, dict):
            continue
        server = field(flow, "server_conn", {}) or {}
        host = _text(field(server, "sni") or field(request, "host"))
        route = _text(field(request, "path")).split("?", 1)[0]
        method = _text(field(request, "method"))
        response = field(flow, "response")
        for direction, message in (("request", request), ("response", response)):
            if not isinstance(message, dict):
                continue
            content_type = headers(message).get("content-type", "").split(";", 1)[0].strip().lower()
            if content_type != "application/x-msgpack":
                continue
            yield CapturedMessage(index, host, route, method, direction,
                                  field(response, "status_code") if isinstance(response, dict) else None,
                                  message_body(message))
