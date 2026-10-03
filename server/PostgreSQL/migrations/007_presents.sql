-- Local rewards only; captured official presents are never imported automatically.
CREATE TABLE public.presents (
    player_id TEXT NOT NULL REFERENCES public.players ON DELETE CASCADE,
    present_id BYTEA NOT NULL CHECK (octet_length(present_id) = 16),
    title TEXT NOT NULL,
    inventory_type INTEGER NOT NULL CHECK (inventory_type > 0),
    inventory_code BIGINT NOT NULL CHECK (inventory_code >= 0),
    amount INTEGER NOT NULL CHECK (amount > 0),
    sender_icon_code BIGINT NOT NULL CHECK (sender_icon_code >= 0),
    arrived_at BIGINT NOT NULL CHECK (arrived_at >= 0),
    limit_date BIGINT CHECK (limit_date > arrived_at),
    received_at BIGINT CHECK (received_at >= arrived_at),
    PRIMARY KEY (player_id, present_id)
);
CREATE INDEX present_pending ON public.presents(player_id, arrived_at, present_id)
    WHERE received_at IS NULL;
CREATE INDEX present_history ON public.presents(player_id, received_at, present_id)
    WHERE received_at IS NOT NULL;
COMMENT ON TABLE public.presents IS 'Player-owned local rewards; receipt and item ledger commit atomically';
