-- Replay storage, protocol catalog and decoded documents. Never store auth headers.
CREATE SCHEMA IF NOT EXISTS mog_local;
CREATE SCHEMA IF NOT EXISTS protocol_data;
CREATE TABLE IF NOT EXISTS mog_local.schema_migrations (
    version TEXT PRIMARY KEY, checksum TEXT NOT NULL,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS mog_local.responses (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source_key TEXT UNIQUE NOT NULL, method TEXT NOT NULL, target TEXT NOT NULL,
    request_hash TEXT NOT NULL, variant TEXT NOT NULL,
    status INTEGER NOT NULL CHECK (status BETWEEN 100 AND 599),
    headers JSONB NOT NULL, body BYTEA NOT NULL,
    captured_at DOUBLE PRECISION NOT NULL, source TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS response_match ON mog_local.responses
    (method, target, request_hash, variant, captured_at DESC, id DESC);
CREATE TABLE IF NOT EXISTS mog_local.requests (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source_key TEXT UNIQUE, created_at DOUBLE PRECISION NOT NULL,
    method TEXT NOT NULL, path TEXT NOT NULL, request_hash TEXT NOT NULL,
    action TEXT NOT NULL, status INTEGER NOT NULL, body_bytes BIGINT NOT NULL,
    elapsed_ms DOUBLE PRECISION NOT NULL
);
CREATE TABLE IF NOT EXISTS mog_local.protocol_models (
    name TEXT PRIMARY KEY, namespace TEXT NOT NULL, base_type TEXT NOT NULL,
    definition JSONB NOT NULL, schema_hash TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS mog_local.protocol_fields (
    model_name TEXT NOT NULL REFERENCES mog_local.protocol_models(name),
    field_index INTEGER NOT NULL, field_name TEXT NOT NULL, csharp_type TEXT NOT NULL,
    sql_type TEXT NOT NULL, PRIMARY KEY (model_name, field_index),
    UNIQUE (model_name, field_name)
);
CREATE TABLE IF NOT EXISTS mog_local.protocol_endpoints (
    method TEXT NOT NULL, path TEXT NOT NULL, request_model TEXT, response_model TEXT,
    interface_name TEXT NOT NULL, method_name TEXT NOT NULL,
    PRIMARY KEY (method, path)
);
CREATE TABLE IF NOT EXISTS mog_local.protocol_documents (
    response_id BIGINT PRIMARY KEY REFERENCES mog_local.responses(id) ON DELETE CASCADE,
    response_model TEXT, named_body JSONB, decode_error TEXT,
    CHECK (named_body IS NOT NULL OR decode_error IS NOT NULL)
);
COMMENT ON SCHEMA protocol_data IS 'Typed protocol observations, not authoritative mutable game state';
COMMENT ON TABLE mog_local.protocol_documents IS 'Raw MessagePack remains in responses.body; unknown fields remain in named_body';
