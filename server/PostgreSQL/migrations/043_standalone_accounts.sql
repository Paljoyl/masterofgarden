-- Local identifiers map to a durable save without captured login responses.
CREATE TABLE public.local_accounts (
    account_hash TEXT PRIMARY KEY CHECK (length(account_hash) = 64),
    player_id TEXT NOT NULL UNIQUE REFERENCES public.players(player_id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
