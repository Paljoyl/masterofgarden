"""Import completed capture responses without replaying any request upstream."""
from pathlib import Path
import logging
import time
from uuid import uuid4
from hashlib import sha256

from PostgreSQL import Database
from mog_protocol.capture import CaptureError, field, headers, message_body, read_flows
from mog_protocol.codec import CodecError

log = logging.getLogger("mog.replay")


def _text(value):
    return value.decode("utf-8", errors="replace") if isinstance(value, bytes) else str(value or "")


def import_captures(database: Database, paths: tuple[Path, ...], api_hosts) -> int:
    count = 0
    for path in paths:
        if not path.exists():
            log.info("Capture not present: %s", path.name)
            continue
        try:
            for index, flow in enumerate(read_flows(path)):
                req, res = field(flow, "request"), field(flow, "response")
                if _text(field(flow, "type")) != "http" or not isinstance(req, dict) or not isinstance(res, dict):
                    continue
                request_headers = headers(req)
                server = field(flow, "server_conn", {}) or {}
                host = _text(request_headers.get("x-mog-original-host") or field(server, "sni")
                             or request_headers.get("host") or field(req, "host")).split(":", 1)[0]
                if host not in api_hosts or headers(res).get("content-type", "").split(";", 1)[0] != "application/x-msgpack":
                    continue
                try:
                    request_body, response_body = message_body(req), message_body(res)
                except CodecError:
                    continue
                request_headers = {k: v for k, v in request_headers.items() if k.lower() != "content-encoding"}
                saved_headers = [(k, v) for k, v in headers(res).items() if k != "content-encoding"]
                timestamp = field(res, "timestamp_end") or field(res, "timestamp_start") or time.time()
                identity = _text(field(flow, "id")) or sha256(response_body + str(timestamp).encode()).hexdigest()
                database.save_response(source_key=f"capture:{path.resolve()}:{index}:{identity}",
                    method=_text(field(req, "method")), target=_text(field(req, "path")),
                    request_body=request_body, request_headers=request_headers,
                    status=field(res, "status_code", 200), headers=saved_headers, body=response_body,
                    captured_at=timestamp, source=path.name)
                count += 1
        except (CaptureError, OSError):
            # Already completed flows remain available if a live writer has a partial tail.
            log.warning("Stopped at incomplete or unavailable capture: %s", path.name)
    return count


def save_live(database, method, target, request_headers, request_body, response):
    # Incoming requests carry raw HTTP bodies. Normalize both before cache matching.
    request_message = {"content": request_body, "headers": list(request_headers.items())}
    response_message = {"content": response.body, "headers": response.headers}
    try:
        request_body = message_body(request_message)
        response_body = message_body(response_message)
    except CodecError:
        return
    normalized_headers = [(k, v) for k, v in response.headers if k.lower() != "content-encoding"]
    database.save_response(source_key="live:" + uuid4().hex, method=method, target=target,
        request_body=request_body, request_headers=request_headers, status=response.status,
        headers=normalized_headers, body=response_body)
