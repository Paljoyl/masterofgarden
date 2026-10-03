"""Run the loopback-only hybrid game API server."""
import argparse
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import logging
import os
from pathlib import Path

from config import ConfigError, DEFAULT_CONFIG, load_config
from PostgreSQL import Database
from local_server.app import Application, Request, json_response
from local_server.transport import end_to_end_headers


class GameHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    # SO_REUSEADDR on Windows allows two servers to own the same live port.
    allow_reuse_address = os.name != "nt"

    def __init__(self, address, app):
        self.app = app
        super().__init__(address, Handler)


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "MogLocal/0.1"

    def log_message(self, *_):
        # Base implementation would log query strings; Application logs only paths.
        pass

    def _reply(self, response):
        self.send_response(response.status)
        for name, value in end_to_end_headers(response.headers):
            if name.lower() not in ("server", "date"):
                self.send_header(name, value)
        self.send_header("X-Mog-Route", response.action)
        self.send_header("Content-Length", str(len(response.body)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.close_connection = True
        if self.command != "HEAD":
            try:
                self.wfile.write(response.body)
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                pass

    def _handle(self):
        self.connection.settimeout(self.server.app.config.timeout + 5)
        if self.headers.get("Transfer-Encoding"):
            self._reply(json_response(400, {"error": "chunked_requests_not_supported"}, "error"))
            return
        lengths = self.headers.get_all("Content-Length", [])
        if len(lengths) > 1:
            self._reply(json_response(400, {"error": "ambiguous_content_length"}, "error"))
            return
        try:
            length = int(lengths[0]) if lengths else 0
        except ValueError:
            self._reply(json_response(400, {"error": "invalid_content_length"}, "error"))
            return
        if length < 0 or length > self.server.app.config.max_body_bytes:
            self._reply(json_response(413, {"error": "request_body_too_large"}, "error"))
            return
        try:
            body = self.rfile.read(length)
        except OSError:
            self._reply(json_response(408, {"error": "request_body_timeout"}, "error"))
            return
        if len(body) != length:
            self._reply(json_response(400, {"error": "incomplete_request_body"}, "error"))
            return
        request = Request(self.command, self.path, dict(self.headers.items()), body, self.client_address[0])
        self._reply(self.server.app.handle(request))

    do_GET = do_POST = do_PUT = do_DELETE = do_PATCH = do_HEAD = _handle


def running_service(config):
    connection = http.client.HTTPConnection(config.host, config.port, timeout=2)
    try:
        connection.request("GET", "/_local/health")
        response = connection.getresponse()
        data = json.loads(response.read(65536))
        return response.status == 200 and isinstance(data, dict) and data.get("service") == "mog-local" and data.get("ok") is True
    except (OSError, ValueError, http.client.HTTPException):
        return False
    finally:
        connection.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description="Master of Garden hybrid local server")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--reuse-running", action="store_true", help="Report an existing healthy project service instead of starting another")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    database = None
    try:
        config = load_config(args.config)
        if args.reuse_running and running_service(config):
            logging.info("Local API is already running at %s. No second instance was started; restart the existing service to apply configuration changes.", config.local_url)
            return 0
        database = Database(config.database)
        app = Application(config, database)
        with GameHTTPServer((config.host, config.port), app) as server:
            logging.info("Local API ready at %s (%s); %s snapshots imported", config.local_url, config.mode, app.imported)
            server.serve_forever(poll_interval=0.25)
    except KeyboardInterrupt:
        pass
    except (ConfigError, OSError) as exc:
        if isinstance(exc, OSError) and (exc.errno in (48, 98, 10048) or getattr(exc, "winerror", None) == 10048):
            logging.error("Port is already in use. Close the previous service using this port before starting another.")
        else:
            logging.error("Server startup failed: %s (OS code %s)", type(exc).__name__, getattr(exc, "winerror", None) or getattr(exc, "errno", None))
        return 1
    finally:
        if database:
            database.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
