-- Local battle starts; no change to existing quest progress or inventory.
CREATE TABLE public.quest_sessions (
    player_id TEXT NOT NULL REFERENCES public.players(player_id) ON DELETE CASCADE,
    quest_unique_id BYTEA NOT NULL CHECK (octet_length(quest_unique_id)=16),
    quest_code BIGINT NOT NULL,
    request_hash TEXT NOT NULL,
    party BYTEA NOT NULL,
    start_response BYTEA NOT NULL,
    stamina_cost BIGINT NOT NULL CHECK (stamina_cost>=0),
    started_at BIGINT NOT NULL,
    state TEXT NOT NULL CHECK (state IN ('active','abandoned','settled')),
    finished_at BIGINT,
    PRIMARY KEY (player_id,quest_unique_id)
);
CREATE UNIQUE INDEX quest_sessions_one_active ON public.quest_sessions(player_id) WHERE state='active';

