"""Storage entry point. Paths retain compatibility with existing SQLite files."""
from hashlib import sha256
from pathlib import Path
import json
import sqlite3
import threading
import time

VARY_HEADERS = ("x-polka-apiversion", "x-polka-buildversion", "x-caravanwa-storeplatformtype")
REPLAY_HEADERS = {"content-type", "x-polka-response-datetime", "x-polka-resourceupdatetoken"}


def request_key(body: bytes):
    return sha256(body).hexdigest()


def variant(headers):
    lower = {k.lower(): v for k, v in headers.items()}
    return json.dumps({k: lower.get(k, "") for k in VARY_HEADERS}, sort_keys=True)


class Database:
    def __new__(cls, path):
        if isinstance(path, dict):
            from .postgres_db import PostgresDatabase
            return PostgresDatabase(path)
        return super().__new__(cls)

    def __init__(self, path: Path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.path = Path(path)
        self.lock = threading.RLock()
        self.connection = sqlite3.connect(str(path), check_same_thread=False)
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.executescript('''
            CREATE TABLE IF NOT EXISTS responses (
                id INTEGER PRIMARY KEY, source_key TEXT UNIQUE NOT NULL,
                method TEXT NOT NULL, target TEXT NOT NULL,
                request_hash TEXT NOT NULL, variant TEXT NOT NULL,
                status INTEGER NOT NULL, headers TEXT NOT NULL, body BLOB NOT NULL,
                captured_at REAL NOT NULL, source TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS response_match ON responses(method,target,request_hash,variant,captured_at);
            CREATE TABLE IF NOT EXISTS requests (
                id INTEGER PRIMARY KEY, created_at REAL NOT NULL,
                method TEXT NOT NULL, path TEXT NOT NULL, request_hash TEXT NOT NULL,
                action TEXT NOT NULL, status INTEGER NOT NULL, body_bytes INTEGER NOT NULL,
                elapsed_ms REAL NOT NULL
            );
        ''')
        self.connection.commit()

    def close(self):
        with self.lock:
            self.connection.close()

    def save_response(self, *, source_key, method, target, request_body, request_headers,
                      status, headers, body, captured_at=None, source="live"):
        # Snapshot headers never include authentication/cookies or hop-by-hop framing.
        saved = [(k, v) for k, v in headers if k.lower() in REPLAY_HEADERS]
        with self.lock, self.connection:
            self.connection.execute('''INSERT OR IGNORE INTO responses
                (source_key,method,target,request_hash,variant,status,headers,body,captured_at,source)
                VALUES(?,?,?,?,?,?,?,?,?,?)''',
                (source_key, method, target, request_key(request_body), variant(request_headers),
                 status, json.dumps(saved), body, captured_at or time.time(), source))

    def lookup(self, method, target, body, request_headers):
        # Exact target includes the query; request body and client version also match.
        with self.lock:
            row = self.connection.execute('''SELECT status,headers,body,source FROM responses
                WHERE method=? AND target=? AND request_hash=? AND variant=? AND status BETWEEN 200 AND 299
                ORDER BY captured_at DESC,id DESC LIMIT 1''',
                (method, target, request_key(body), variant(request_headers))).fetchone()
        if row is None:
            return None
        return {"status": row[0], "headers": json.loads(row[1]), "body": bytes(row[2]), "source": row[3]}

    def history(self, limit=50):
        with self.lock:
            rows = self.connection.execute('''SELECT id,created_at,method,path,action,status,body_bytes,elapsed_ms
                FROM requests ORDER BY id DESC LIMIT ?''', (limit,)).fetchall()
        names = ("id", "created_at", "method", "path", "action", "status", "body_bytes", "elapsed_ms")
        return [dict(zip(names, row)) for row in rows]

    def record(self, method, path, body, action, status, elapsed_ms):
        with self.lock, self.connection:
            self.connection.execute('''INSERT INTO requests
                (created_at,method,path,request_hash,action,status,body_bytes,elapsed_ms) VALUES(?,?,?,?,?,?,?,?)''',
                (time.time(), method, path, request_key(body), action, status, len(body), elapsed_ms))

    def summary(self):
        with self.lock:
            snapshots = self.connection.execute("SELECT COUNT(*) FROM responses").fetchone()[0]
            requests = self.connection.execute("SELECT COUNT(*) FROM requests").fetchone()[0]
            modes = dict(self.connection.execute("SELECT action,COUNT(*) FROM requests GROUP BY action"))
        return {"snapshots": snapshots, "requests": requests, "actions": modes}
