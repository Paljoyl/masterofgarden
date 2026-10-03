"""Validated configuration shared by the service and the mitmproxy bridge."""
from dataclasses import dataclass
from pathlib import Path
import json
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
DEFAULT_CONFIG = ROOT.parent / "runtime/server.config.json"

# Catalog endpoints used by the initial configuration and route diagnostics.
CATALOG_ROUTES = ("POST /lottery/getlotteries",
                  "POST /lottery/getlotterywinningchance")


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class ServerConfig:
    host: str
    port: int
    upstream: str
    api_hosts: tuple[str, ...]
    database: Path | dict
    captures: tuple[Path, ...]
    overrides: Path
    mode: str
    timeout: float
    upstream_proxy: str
    routes: dict[str, str]
    forward_prefixes: tuple[str, ...]
    max_body_bytes: int
    standalone: bool = False

    def __post_init__(self):
        # Legacy configurations remain readable; global fallback is always local.
        object.__setattr__(self, "mode", "local")

    @property
    def local_url(self):
        return f"http://{self.host}:{self.port}"

    def action(self, method: str, path: str):
        explicit = self.routes.get(method.upper() + " " + path)
        if explicit:
            return explicit
        if any(path.startswith(prefix) for prefix in self.forward_prefixes):
            return "forward"
        return "local"


def load_config(path: Path = DEFAULT_CONFIG) -> ServerConfig:
    path = Path(path).resolve()
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        bind = data.get("listen", {})
        host, port = bind.get("host", "127.0.0.1"), bind.get("port", 18080)
        if host != "127.0.0.1" or type(port) is not int or not 1 <= port <= 65535:
            raise ConfigError("Local server must bind to 127.0.0.1 and a valid port")
        upstream = data["upstream"].rstrip("/")
        target = urlsplit(upstream)
        if target.scheme not in ("https", "http") or not target.hostname or target.username or target.password or target.path or target.query or target.fragment:
            raise ConfigError("upstream must be a plain HTTP(S) origin")
        standalone = data.get("standalone", True)
        if type(standalone) is not bool:
            raise ConfigError("standalone must be boolean")
        mode = "local"
        routes = data.get("routes", {})
        if not isinstance(routes, dict) or any(v not in ("local", "replay", "forward", "replay_then_forward") for v in routes.values()):
            raise ConfigError("Invalid route actions")
        api_hosts = tuple(data.get("api_hosts", [target.hostname]))
        if not api_hosts or any(not isinstance(h, str) or not h or "/" in h or ":" in h for h in api_hosts):
            raise ConfigError("api_hosts must contain plain domain names")
        timeout = float(data.get("timeout_seconds", 20))
        if not 0 < timeout <= 120:
            raise ConfigError("timeout_seconds must be between 0 and 120")
        proxy = data.get("upstream_proxy", "auto")
        if proxy not in ("auto", "", "direct"):
            parsed = urlsplit(proxy)
            if parsed.scheme != "http" or not parsed.hostname or parsed.username or parsed.password:
                raise ConfigError("upstream_proxy must be auto, direct, or an HTTP proxy URL")
        prefixes = tuple(data.get("forward_prefixes", []))
        if any(not isinstance(p, str) or not p.startswith("/") for p in prefixes):
            raise ConfigError("forward_prefixes must be path prefixes")
        maximum = data.get("max_body_bytes", 64 * 1024 * 1024)
        if type(maximum) is not int or not 1 <= maximum <= 64 * 1024 * 1024:
            raise ConfigError("Invalid max_body_bytes")
        if standalone and (data.get("captures") or prefixes or any(v != "local" for v in routes.values())):
            raise ConfigError("Standalone mode requires empty captures and local-only routes")
        resolve = lambda value: (path.parent / value).resolve()
        database = data.get("database", "data/local.sqlite3")
        if isinstance(database, dict):
            database = dict(database)
            if database.get("driver") != "postgresql" or database.get("host", "127.0.0.1") not in ("127.0.0.1", "localhost", "::1"):
                raise ConfigError("database must use PostgreSQL on localhost")
            if not isinstance(database.get("dbname"), str) or not database["dbname"]:
                raise ConfigError("database.dbname is required")
            if type(database.get("port", 5432)) is not int or not 1 <= database.get("port", 5432) <= 65535:
                raise ConfigError("Invalid database.port")
            if database["dbname"].casefold() == "Ｍaster of Garden".casefold():
                raise ConfigError("Use an independent public-project database")
            if "password" in database:
                raise ConfigError("Use database.password_file or password_env instead of an inline password")
            if database.get("password_file"):
                database["password_file"] = resolve(database["password_file"])
        else:
            database = resolve(database)
        return ServerConfig(host, port, upstream, api_hosts,
                            database,
                            tuple(resolve(p) for p in data.get("captures", [])),
                            resolve(data.get("overrides", "data/overrides")), mode, timeout,
                            proxy, routes, prefixes, maximum, standalone)
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        if isinstance(exc, ConfigError):
            raise
        raise ConfigError("Cannot load server configuration: " + type(exc).__name__) from exc
