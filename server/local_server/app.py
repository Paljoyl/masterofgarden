"""Routing policy and protocol handlers, testable without a network listener."""
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import time
import traceback
from urllib.parse import urlsplit

from config import CATALOG_ROUTES, ServerConfig
from local_routes import RESOURCE_ROUTE
from PostgreSQL import Database
from PostgreSQL.db import variant
from PostgreSQL.timed import TimeBusinessError
from psycopg import Error as StorageError, IntegrityError
from mog_protocol.capture import message_body
from mog_protocol.codec import CodecError, DOCUMENT_FORMAT, decode, encode, encode_document, to_jsonable
from mog_protocol.schema import SchemaRegistry
from .replay import import_captures, save_live
from .transport import Response, Upstream, UpstreamError
from .protocol import LocalError, Protocol
from .resources import installed_resource_hashes
from .handlers import HandlerRegistry
from .services.player import PlayerService
from .services.standalone import StandalonePlayerService

log = logging.getLogger("mog.api")


@dataclass
class Request:
    method: str
    target: str
    headers: dict[str, str]
    body: bytes
    client_ip: str = "127.0.0.1"

    @property
    def path(self):
        return urlsplit(self.target).path


def json_response(status, data, action="local"):
    return Response(status, [("Content-Type", "application/json; charset=utf-8")],
                    json.dumps(data, ensure_ascii=False).encode("utf-8"), action)


def replay_response(snapshot, action="replay"):
    saved = [(k, v) for k, v in snapshot["headers"] if k.lower() != "x-polka-response-datetime"]
    saved.append(("X-Polka-Response-DateTime", datetime.now(timezone.utc).isoformat()))
    return Response(snapshot["status"], saved, snapshot["body"], action)


class Application:
    def __init__(self, config: ServerConfig, database: Database, upstream=None, *, seed=True, player_service=None):
        self.config = config
        self.database = database
        self.upstream = upstream or Upstream(config.upstream, config.timeout, config.upstream_proxy, config.max_body_bytes)
        # A local action must report missing odds before the client gives up.
        self.lottery_upstream = upstream or Upstream(config.upstream, min(config.timeout, 3),
                                                   config.upstream_proxy, config.max_body_bytes)
        self.registry = SchemaRegistry()
        self.config.overrides.mkdir(parents=True, exist_ok=True)
        self.imported = import_captures(database, config.captures, config.api_hosts) if seed and not config.standalone else 0
        repository = getattr(database, "players", None)
        self.player_imported = repository.seed_from_snapshots() if seed and repository and not config.standalone else None
        self.protocol = Protocol(self.registry)
        self.players = player_service or (StandalonePlayerService(repository, self.protocol) if config.standalone else
            PlayerService(repository, self.protocol, config.captures if seed else (), config.api_hosts))
        self.present_imported = self.players.seed_present_boxes() if seed and repository and not config.standalone else 0
        if self.present_imported:
            log.info('Initialized %s captured unclaimed presents in local storage', self.present_imported)
        self.handlers = HandlerRegistry(self.players, self.protocol, self._lottery_chances)

    def _lottery_chances(self, request, code):
        if self.config.standalone:
            return None
        # This fixed read-only query supplies stripped server-side rates.
        # Exact body + client variant prevents borrowing another pool's odds.
        headers = {k: v for k, v in request.headers.items()
                   if k.lower() not in ('content-encoding', 'content-length', 'content-type')}
        headers['Content-Type'] = 'application/x-msgpack'
        query = Request('POST', '/lottery/getlotterywinningchance', headers, encode([code]), request.client_ip)
        try:
            snapshot = self._snapshot(query)
            if snapshot is None and self.handlers.lottery.catalog.fallback_enabled:
                # The lottery service builds and validates local odds against its
                # actual lineup and button. Do not require an old official session.
                return None
            response = replay_response(snapshot) if snapshot is not None else self._forward(query, upstream=self.lottery_upstream)
            if response.status != 200:
                log.warning('Lottery probability rejected: pool=%s, upstream_status=%s', code, response.status)
                raise LocalError('local_lottery_probability_unavailable', 503)
            body = decode(message_body({'content': response.body, 'headers': response.headers}))
            self.protocol.fields('GetLotteryWinningChanceResponse', body, strict=True)
            return body
        except (UpstreamError, CodecError, LocalError, TypeError, ValueError) as exc:
            log.warning('Lottery probability unavailable: pool=%s, reason=%s', code,
                        exc.code if isinstance(exc, LocalError) else
                        type(exc.__cause__).__name__ if isinstance(exc, UpstreamError) and exc.__cause__ else
                        type(exc).__name__)
            raise LocalError('local_lottery_probability_unavailable', 503) from exc

    def _snapshot(self, request):
        body = message_body({"content": request.body, "headers": list(request.headers.items())})
        return self.database.lookup(request.method, request.target, body, request.headers)

    def _override(self, request):
        if any(ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789/_-" for ch in request.path):
            return None
        filename = request.method + "_" + request.path.strip("/").replace("/", "__") + ".json"
        path = self.config.overrides / filename
        if not path.is_file():
            return None
        try:
            document = json.loads(path.read_text(encoding="utf-8-sig"))
            if document.get("format") == "mog-named-msgpack-v1":
                model = document.get("type")
                if model not in self.registry.models:
                    raise CodecError("Unknown override response model")
                positional = self.registry.positional(document["value"], model)
                converted = {"format": DOCUMENT_FORMAT, "value": to_jsonable(positional)}
                if "original_hex" in document:
                    converted["original_hex"] = document["original_hex"]
                payload = encode_document(converted)
            else:
                payload = encode_document(document)
        except (ValueError, KeyError, TypeError, OSError) as exc:
            raise CodecError("Invalid local response override: " + path.name) from exc
        return Response(200, [("Content-Type", "application/x-msgpack"),
                    ("X-Polka-Response-DateTime", datetime.now(timezone.utc).isoformat())], payload, "local-override")

    def _resource_hashes(self, request):
        if self.config.standalone:
            return self.protocol.response(request, {"LatestAssetBundleHashes": installed_resource_hashes(),
                "ClientIpAddress": request.client_ip})
        snapshot = self._snapshot(request)
        if snapshot is None:
            return None
        value = decode(snapshot["body"])
        if not isinstance(value, list) or len(value) < 2 or not isinstance(value[0], dict):
            raise CodecError("Resource hash snapshot has an unexpected model layout")
        # Generate this stable API locally, rather than serving an old captured IP.
        value[1] = request.client_ip
        result = replay_response(snapshot, "local")
        result.body = encode(value)
        return result

    def _forward(self, request, *, upstream=None):
        if self.config.standalone:
            raise LocalError("upstream_disabled_in_standalone_mode", 501)
        relay_headers = request.headers
        local_token = any(k.lower() == "x-polka-loginkey" and v.startswith("mog-local-")
                          for k, v in request.headers.items())
        if local_token:
            relay_headers = self.players.sessions.relay_headers(request.headers, variant(request.headers))
        response = (upstream or self.upstream).request(request.method, request.target, relay_headers, request.body)
        if (local_token and self.players.timing is not None and response.status == 200
                and request.path == '/lottery/getlotteries'):
            fields = self.protocol.fields('GetLotteriesResponse', decode(message_body({
                'content': response.body, 'headers': response.headers})))
            fields['LotteryDisplays'] = self.handlers.lottery.displays(request, fields['LotteryDisplays'])
            response.body = encode(self.protocol.model('GetLotteriesResponse', fields))
            response.headers = [(k, v) for k, v in response.headers
                                if k.lower() not in ('content-encoding', 'content-length')]
        if 200 <= response.status < 300:
            try:
                save_live(self.database, request.method, request.target, request.headers, request.body, response)
            except Exception as exc:
                # A cache failure must not turn an already-completed real action into a retry.
                log.warning("Could not cache upstream response: %s", type(exc).__name__)
        return response

    def _dispatch(self, request):
        if request.method == "GET" and request.path == "/_local/health":
            return json_response(200, {"ok": True, "service": "mog-local", "mode": self.config.mode,
                "database": self.database.summary(), "imported": self.imported, "player_imported": self.player_imported,
                "local_handlers": len(self.handlers.routes) + 1})
        if request.method == "GET" and request.path == "/_local/routes":
            return json_response(200, {"routes": self.config.routes,
                "forward_prefixes": self.config.forward_prefixes,
                "mode": "local",
                "local_handlers": sorted(set(self.handlers.routes) | {RESOURCE_ROUTE}),
                "catalog_routes": list(CATALOG_ROUTES),
                "fallback": "local handler; unimplemented returns 501"})
        if request.method == "GET" and request.path == "/_local/history":
            return json_response(200, {"requests": self.database.history()})
        if request.path.startswith("/_local/"):
            return json_response(404, {"error": "unknown_local_endpoint"}, "error")
        # Accept only the configured game API origins, never an arbitrary redirect URL.
        lower = {k.lower(): v for k, v in request.headers.items()}
        original_host = lower.get("x-mog-original-host", "")
        if original_host and original_host not in self.config.api_hosts:
            return json_response(400, {"error": "unexpected_game_api_host"}, "error")
        action = self.config.action(request.method, request.path)
        if action == "forward":
            return self._forward(request)
        if action == "local":
            if urlsplit(request.target).query:
                raise LocalError("local_query_parameters_not_supported")
            response = self.handlers.dispatch(request)
            if response is not None:
                return response
            if request.method + " " + request.path != RESOURCE_ROUTE:
                raise LocalError("local_endpoint_not_implemented", 501)
        override = self._override(request)
        if override is not None:
            return override
        if action == "local" and request.method + " " + request.path == RESOURCE_ROUTE:
            response = self._resource_hashes(request)
            if response is not None:
                return response
            raise LocalError("local_resource_seed_not_found", 503)
        if action == "local":
            raise LocalError("local_endpoint_not_implemented", 501)
        if action in ("replay", "replay_then_forward"):
            snapshot = self._snapshot(request)
            if snapshot is not None:
                return replay_response(snapshot)
        if action == "replay":
            return json_response(503, {"error": "replay_not_found", "path": request.path}, "replay-miss")
        return self._forward(request)

    def handle(self, request: Request) -> Response:
        # Validate before parsing or recording: urlsplit can raise on malformed authorities
        # and silently strips some controls, which must not change routing or cache identity.
        if (not request.target.startswith('/') or request.target.startswith('//')
                or '#' in request.target or any(ord(ch) <= 32 or ord(ch) == 127 for ch in request.target)):
            return json_response(400, {'error': 'invalid_request_target'}, 'error')
        start = time.perf_counter()
        try:
            response = self._dispatch(request)
        except CodecError:
            response = json_response(400, {"error": "invalid_local_protocol_data"}, "error")
        except (LocalError, TimeBusinessError) as exc:
            log.warning('Local request rejected: %s %s, reason=%s', request.method, request.path, exc.code)
            if isinstance(exc, LocalError) and exc.client_message is not None:
                response = self.protocol.common_error_response(exc.status, exc.client_message)
            else:
                response = json_response(exc.status, {"error": exc.code, "path": request.path}, "local-error")
        except (KeyError, IndexError) as exc:
            # Log locations only: exception values can contain player data or tokens.
            frames = traceback.extract_tb(exc.__traceback__)
            locations = ' -> '.join(f'{Path(frame.filename).name}:{frame.lineno}:{frame.name}'
                                    for frame in frames)
            log.error('Local definition lookup failed (%s): %s', type(exc).__name__, locations)
            response = json_response(503, {"error": "local_business_configuration_invalid", "path": request.path}, "local-error")
        except LookupError:
            response = json_response(503, {"error": "local_player_not_initialized", "path": request.path}, "local-error")
        except IntegrityError:
            response = json_response(409, {"error": "local_state_constraint_conflict", "path": request.path}, "local-error")
        except StorageError as exc:
            log.warning("Player storage failed: %s", type(exc).__name__)
            response = json_response(503, {"error": "player_storage_unavailable", "path": request.path}, "local-error")
        except UpstreamError as exc:
            log.warning("Forward failed: %s %s (%s)", request.method, request.path, type(exc).__name__)
            # Never silently replay forced-live catalog/login routes after a failure.
            response = json_response(502, {"error": "upstream_unavailable", "path": request.path}, "forward-error")
        elapsed = round((time.perf_counter() - start) * 1000, 2)
        if not request.path.startswith("/_local/"):
            try:
                self.database.record(request.method, request.path, request.body, response.action, response.status, elapsed)
            except Exception as exc:
                log.warning("Could not save request history: %s", type(exc).__name__)
            log.info("%s %s -> %s %s (%s ms)", request.method, request.path, response.action, response.status, elapsed)
        return response
