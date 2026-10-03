"""One-shot HTTP transport: preserve binary bodies and current client auth."""
from dataclasses import dataclass
import http.client
import ssl
from urllib.parse import urlsplit
from urllib.request import getproxies, proxy_bypass

HOP_HEADERS = {"connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
               "te", "trailer", "transfer-encoding", "upgrade", "content-length", "host", "expect"}


class UpstreamError(Exception):
    pass


@dataclass
class Response:
    status: int
    headers: list[tuple[str, str]]
    body: bytes
    action: str


def end_to_end_headers(headers, *, request=False):
    pairs = list(headers.items()) if isinstance(headers, dict) else list(headers)
    connection = set()
    for name, value in pairs:
        if name.lower() == "connection":
            connection.update(v.strip().lower() for v in value.split(","))
    excluded = HOP_HEADERS | connection
    return [(k, v) for k, v in pairs if k.lower() not in excluded and not k.lower().startswith("x-mog-")]


class Upstream:
    def __init__(self, origin: str, timeout: float, proxy: str, max_body_bytes: int):
        self.origin = urlsplit(origin)
        self.timeout = timeout
        self.proxy = proxy
        self.maximum = max_body_bytes

    def _proxy(self):
        if self.proxy in ("", "direct"):
            return None
        if self.proxy != "auto":
            return urlsplit(self.proxy)
        if proxy_bypass(self.origin.hostname):
            return None
        proxies = getproxies()
        value = proxies.get(self.origin.scheme) or proxies.get("http")
        if not value:
            return None
        proxy = urlsplit(value if "://" in value else "http://" + value)
        if proxy.scheme != "http" or proxy.username or proxy.password:
            raise UpstreamError("Unsupported automatic proxy configuration")
        return proxy

    def request(self, method: str, target: str, headers: dict, body: bytes) -> Response:
        if not target.startswith("/") or target.startswith("//") or "\r" in target or "\n" in target:
            raise UpstreamError("Invalid upstream request path")
        origin = self.origin
        connection = None
        try:
            proxy = self._proxy()
            port = origin.port or (443 if origin.scheme == "https" else 80)
            if origin.scheme == "https":
                # HTTPSConnection performs CONNECT before TLS when a tunnel is set.
                connection = http.client.HTTPSConnection(proxy.hostname if proxy else origin.hostname,
                    proxy.port or 80 if proxy else port, timeout=self.timeout, context=ssl.create_default_context())
                if proxy:
                    connection.set_tunnel(origin.hostname, port)
                destination = target
            else:
                connection = http.client.HTTPConnection(proxy.hostname if proxy else origin.hostname,
                    proxy.port or 80 if proxy else port, timeout=self.timeout)
                destination = origin.geturl().rstrip("/") + target if proxy else target
            forwarded = dict(end_to_end_headers(headers, request=True))
            forwarded["Host"] = origin.netloc
            # Store replayable identity bytes, independent of the client's compression support.
            forwarded = {k: v for k, v in forwarded.items() if k.lower() != "accept-encoding"}
            forwarded["Accept-Encoding"] = "identity"
            connection.request(method, destination, body=body, headers=forwarded)
            remote = connection.getresponse()
            payload = remote.read(self.maximum + 1)
            if len(payload) > self.maximum:
                raise UpstreamError("Upstream response exceeds the body limit")
            return Response(remote.status, end_to_end_headers(remote.getheaders()), payload, "forward")
        except (OSError, http.client.HTTPException, ValueError) as exc:
            # Exceptions may embed sensitive URL/query data; never log their raw text.
            raise UpstreamError("Upstream connection failed: " + type(exc).__name__) from exc
        finally:
            if connection:
                connection.close()
