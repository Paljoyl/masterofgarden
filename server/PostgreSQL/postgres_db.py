"""PostgreSQL connection, migrations, current player state and raw replay storage."""
from hashlib import sha256
import json
import os
from pathlib import Path
import sqlite3
import threading
import time

import psycopg
from psycopg.types.json import Jsonb

from .db import REPLAY_HEADERS, request_key, variant
from mog_protocol.schema import SchemaRegistry

DATABASE_ROOT = Path(__file__).resolve().parent


class DatabaseError(OSError):
    """A storage failure whose message contains no connection credentials."""


def connection_options(settings):
    options = {key: settings[key] for key in ("host", "port", "dbname", "user") if key in settings}
    options.setdefault("host", "127.0.0.1")
    options.setdefault("user", "postgres")
    password = os.environ.get(settings.get("password_env", "MOG_DB_PASSWORD"))
    if password is None and settings.get("password_file"):
        password = Path(settings["password_file"]).read_text(encoding="utf-8").rstrip("\r\n")
    if password is not None:
        options["password"] = password
    options.update(connect_timeout=5, application_name="mog-local")
    return options


class PostgresDatabase:
    def __init__(self, settings):
        self.lock = threading.RLock()
        self.registry = SchemaRegistry()
        self.connection = None
        try:
            self.connection = psycopg.connect(**connection_options(settings), autocommit=True)
            self.initialize()
            from .players import PlayerRepository
            self.players = PlayerRepository(self)
        except Exception as exc:
            if self.connection is not None:
                self.connection.close()
            raise DatabaseError("PostgreSQL initialization failed (" + type(exc).__name__ + ")") from exc

    def initialize(self):
        with self.lock, self.connection.transaction():
            self.connection.execute("SELECT pg_advisory_xact_lock(7140928361)")
            self.connection.execute("CREATE SCHEMA IF NOT EXISTS mog_local")
            self.connection.execute("CREATE TABLE IF NOT EXISTS mog_local.schema_migrations (version TEXT PRIMARY KEY, checksum TEXT NOT NULL, applied_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP)")
            active = sorted((DATABASE_ROOT / "migrations").glob("*.sql"))
            archived = sorted((DATABASE_ROOT / "migrations/legacy").glob("*.sql"))
            for path in active + archived:
                content = path.read_text(encoding="utf-8")
                checksum = sha256(content.encode()).hexdigest()
                applied = self.connection.execute("SELECT checksum FROM mog_local.schema_migrations WHERE version=%s", (path.name,)).fetchone()
                if applied:
                    if applied[0] != checksum:
                        error = DatabaseError("Applied migration changed: " + path.name)
                        error.migration = path.name
                        raise error
                    continue
                if path.parent.name == "legacy":
                    continue
                try:
                    self.connection.execute(content)
                except psycopg.Error as exc:
                    error = DatabaseError("Migration failed: " + path.name)
                    error.migration = path.name
                    raise error from exc
                self.connection.execute("INSERT INTO mog_local.schema_migrations(version,checksum) VALUES (%s,%s)", (path.name, checksum))
            self.connection.execute("""ALTER TABLE public.players
                ADD COLUMN IF NOT EXISTS home_character_costume_code BIGINT,
                ADD COLUMN IF NOT EXISTS home_situations JSONB,
                ADD COLUMN IF NOT EXISTS home_characters JSONB,
                ADD COLUMN IF NOT EXISTS home_quiz_answers JSONB""")
            old_home = self.connection.execute(
                "SELECT to_regclass('mog_local.player_home_state') IS NOT NULL").fetchone()[0]
            if old_home:
                self.connection.execute("""UPDATE public.players AS p SET
                    home_character_costume_code = h.character_costume_code,
                    home_situations = h.situations,
                    home_characters = h.home_characters,
                    home_quiz_answers = h.quiz_answers
                    FROM mog_local.player_home_state AS h
                    WHERE p.player_id = h.player_id
                      AND p.home_character_costume_code IS NULL""")
            old_public_home = self.connection.execute(
                "SELECT to_regclass('public.player_home_state') IS NOT NULL").fetchone()[0]
            if old_public_home:
                self.connection.execute("""UPDATE public.players AS p SET
                    home_character_costume_code = h.character_costume_code,
                    home_situations = h.situations,
                    home_characters = h.home_characters,
                    home_quiz_answers = h.quiz_answers
                    FROM public.player_home_state AS h
                    WHERE p.player_id = h.player_id
                      AND p.home_character_costume_code IS NULL""")

    def close(self):
        with self.lock:
            self.connection.close()

    def _insert_snapshot(self, row):
        result = self.connection.execute('''INSERT INTO mog_local.responses
            (source_key,method,target,request_hash,variant,status,headers,body,captured_at,source)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT(source_key) DO NOTHING RETURNING id''', row).fetchone()
        return bool(result)

    def save_response(self, *, source_key, method, target, request_body, request_headers,
                      status, headers, body, captured_at=None, source="live"):
        saved = [(k, v) for k, v in headers if k.lower() in REPLAY_HEADERS]
        row = (source_key, method, target, request_key(request_body), variant(request_headers),
               status, Jsonb(saved), body, time.time() if captured_at is None else captured_at, source)
        with self.lock, self.connection.transaction():
            self._insert_snapshot(row)

    def lookup(self, method, target, body, request_headers):
        with self.lock:
            row = self.connection.execute('''SELECT status,headers,body,source FROM mog_local.responses
                WHERE method=%s AND target=%s AND request_hash=%s AND variant=%s AND status BETWEEN 200 AND 299
                ORDER BY captured_at DESC,id DESC LIMIT 1''',
                (method, target, request_key(body), variant(request_headers))).fetchone()
        return None if row is None else {"status": row[0], "headers": row[1], "body": bytes(row[2]), "source": row[3]}

    def record(self, method, path, body, action, status, elapsed_ms):
        with self.lock:
            self.connection.execute('''INSERT INTO mog_local.requests
                (created_at,method,path,request_hash,action,status,body_bytes,elapsed_ms)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)''',
                (time.time(), method, path, request_key(body), action, status, len(body), elapsed_ms))

    def history(self, limit=50):
        with self.lock:
            rows = self.connection.execute('''SELECT id,created_at,method,path,action,status,body_bytes,elapsed_ms
                FROM mog_local.requests ORDER BY id DESC LIMIT %s''', (limit,)).fetchall()
        names = ("id", "created_at", "method", "path", "action", "status", "body_bytes", "elapsed_ms")
        return [dict(zip(names, row)) for row in rows]

    def summary(self):
        with self.lock:
            counts = self.connection.execute("SELECT (SELECT count(*) FROM mog_local.responses),(SELECT count(*) FROM mog_local.requests)").fetchone()
            actions = dict(self.connection.execute("SELECT action,count(*) FROM mog_local.requests GROUP BY action").fetchall())
        return dict(backend="postgresql", snapshots=counts[0], requests=counts[1], actions=actions,
                    player_state=self.players.summary())

    def import_sqlite(self, path):
        source = sqlite3.connect(Path(path).resolve().as_uri() + "?mode=ro", uri=True)
        added_responses = added_requests = 0
        try:
            source.execute("BEGIN")
            with self.lock, self.connection.transaction():
                for row in source.execute('''SELECT source_key,method,target,request_hash,variant,status,headers,body,captured_at,source FROM responses ORDER BY id'''):
                    row = list(row)
                    row[6] = Jsonb([(k, v) for k, v in json.loads(row[6]) if k.lower() in REPLAY_HEADERS])
                    added_responses += self._insert_snapshot(row)
                for row in source.execute('''SELECT id,created_at,method,path,request_hash,action,status,body_bytes,elapsed_ms FROM requests ORDER BY id'''):
                    identity = "sqlite:" + str(Path(path).resolve()) + ":" + str(row[0])
                    result = self.connection.execute('''INSERT INTO mog_local.requests
                        (source_key,created_at,method,path,request_hash,action,status,body_bytes,elapsed_ms)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(source_key) DO NOTHING RETURNING id''',
                        (identity, *row[1:])).fetchone()
                    added_requests += result is not None
        finally:
            source.close()
        return {"responses_added": added_responses, "requests_added": added_requests}
