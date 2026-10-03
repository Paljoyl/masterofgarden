"""Server-issued local sessions; official login keys never become local identity."""
from dataclasses import dataclass
from hashlib import sha256
import secrets
import threading
import time

from ..protocol import LocalError


@dataclass(frozen=True)
class Session:
    player_id: str
    variant: str
    expires_at: float
    upstream_key: str | None


class Sessions:
    def __init__(self, ttl=24 * 60 * 60, clock=time.time, *, store=None, upstream_key_provider=None):
        self.ttl, self.clock = ttl, clock
        self.store, self.upstream_key_provider = store, upstream_key_provider
        self._sessions = {}
        self._lock = threading.RLock()

    def issue(self, player_id, variant, upstream_key=None):
        token = "mog-local-" + secrets.token_hex(32)
        now = self.clock()
        digest = sha256(token.encode()).digest()
        session = Session(player_id, variant, now + self.ttl, upstream_key)
        # Persist before returning a token. Never hold the memory lock while
        # acquiring the repository lock, including when called inside a login.
        if self.store is not None:
            self.store.save(digest, player_id, variant, now, session.expires_at)
        with self._lock:
            self._sessions = {k: v for k, v in self._sessions.items() if v.expires_at > now}
            self._sessions[digest] = session
        return token

    def resolve(self, headers, variant):
        lower = {k.lower(): v for k, v in headers.items()}
        token = lower.get("x-polka-loginkey", "")
        # A prefix alone never authenticates a request. Restore only the exact
        # digest previously issued by this server, with its original expiry.
        if not token.startswith('mog-local-') or len(token) != 74:
            raise LocalError("local_session_required", 401)
        digest, now = sha256(token.encode()).digest(), self.clock()
        with self._lock:
            session = self._sessions.get(digest)
        if session is None and self.store is not None:
            row = self.store.load(digest, variant, now)
            if row is not None:
                session = Session(row[0], row[1], row[2], None)
        if session is None or session.expires_at <= now or session.variant != variant:
            raise LocalError("local_session_required", 401)
        if session.upstream_key is None and self.upstream_key_provider is not None:
            session = Session(session.player_id, session.variant, session.expires_at,
                              self.upstream_key_provider(session.player_id, session.variant))
        with self._lock:
            self._sessions[digest] = session
        return session

    def relay_headers(self, headers, variant):
        session = self.resolve(headers, variant)
        if not session.upstream_key or session.upstream_key.startswith('mog-local-'):
            raise LocalError("catalog_session_unavailable", 503)
        result = {k: v for k, v in headers.items() if k.lower() != "x-polka-loginkey"}
        result["X-Polka-LoginKey"] = session.upstream_key
        return result
