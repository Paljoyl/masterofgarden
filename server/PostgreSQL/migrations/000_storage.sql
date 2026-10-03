-- Minimal replay/history storage used by the hybrid server alongside public state.
CREATE SCHEMA IF NOT EXISTS mog_local;
CREATE TABLE IF NOT EXISTS mog_local.responses (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source_key TEXT UNIQUE NOT NULL, method TEXT NOT NULL, target TEXT NOT NULL,
    request_hash TEXT NOT NULL, variant TEXT NOT NULL,
    status INTEGER NOT NULL CHECK (status BETWEEN 100 AND 599),
    headers JSONB NOT NULL, body BYTEA NOT NULL,
    captured_at DOUBLE PRECISION NOT NULL, source TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS response_match ON mog_local.responses
    (method,target,request_hash,variant,captured_at DESC,id DESC);
CREATE TABLE IF NOT EXISTS mog_local.requests (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source_key TEXT UNIQUE, created_at DOUBLE PRECISION NOT NULL,
    method TEXT NOT NULL, path TEXT NOT NULL, request_hash TEXT NOT NULL,
    action TEXT NOT NULL, status INTEGER NOT NULL, body_bytes BIGINT NOT NULL,
    elapsed_ms DOUBLE PRECISION NOT NULL
);
