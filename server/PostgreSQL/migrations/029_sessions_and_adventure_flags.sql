-- New authentication/branch records only. Preserve all existing player state.
-- Store local token hashes, never plaintext tokens or official relay credentials.
CREATE TABLE public.player_sessions (
    token_hash BYTEA PRIMARY KEY CHECK (octet_length(token_hash)=32),
    player_id TEXT NOT NULL REFERENCES public.players(player_id) ON DELETE CASCADE,
    variant TEXT NOT NULL,
    issued_at DOUBLE PRECISION NOT NULL,
    expires_at DOUBLE PRECISION NOT NULL CHECK (expires_at>issued_at)
);
CREATE INDEX player_sessions_player ON public.player_sessions(player_id);

CREATE TABLE public.player_adventure_flags (
    player_id TEXT NOT NULL REFERENCES public.players(player_id) ON DELETE CASCADE,
    flag_code BIGINT NOT NULL,
    flag_value BIGINT NOT NULL CHECK (flag_value>=0),
    updated_at BIGINT NOT NULL,
    PRIMARY KEY (player_id,flag_code)
);
