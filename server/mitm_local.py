"""Route only game API hosts into the local server. Other traffic passes unchanged.

The frozen mitmproxy binary needs no external dependencies for this bridge.
"""
from pathlib import Path
import sys

from mitmproxy import ctx

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from config import load_config


class LocalRouter:
    def load(self, loader):
        loader.add_option("mog_config", str, str(ROOT / "config.json"), "Local game server configuration")

    def configure(self, updated):
        if "mog_config" in updated or not hasattr(self, "config"):
            self.config = load_config(Path(ctx.options.mog_config))

    def request(self, flow):
        config = self.config
        candidates = (flow.server_conn.sni, flow.client_conn.sni, flow.request.pretty_host, flow.request.host)
        origin = next((h for h in candidates if h in config.api_hosts), None)
        if origin is None:
            return
        flow.metadata["mog_original_host"] = origin
        flow.metadata["mog_original_url"] = flow.request.url
        flow.request.headers["X-Mog-Original-Host"] = origin
        flow.request.scheme = "http"
        flow.request.host = config.host
        flow.request.port = config.port
        # Preserve the game's API Host while the actual TCP destination is loopback.
        flow.request.headers["Host"] = origin

    def response(self, flow):
        if "mog_original_host" not in flow.metadata or flow.response is None:
            return
        route = flow.response.headers.get("X-Mog-Route", "unknown")
        flow.metadata["mog_route"] = route
        flow.comment = "mog-local: " + route


addons = [LocalRouter()]
