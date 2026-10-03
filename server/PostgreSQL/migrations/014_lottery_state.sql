-- Local lottery execution state, independent of official orders and replay bytes.
CREATE TABLE public.player_lottery_state (
    player_id TEXT PRIMARY KEY REFERENCES public.players(player_id) ON DELETE CASCADE,
    initialized_at BIGINT NOT NULL
);
CREATE TABLE public.lottery_button_counts (
    player_id TEXT NOT NULL REFERENCES public.players(player_id) ON DELETE CASCADE,
    lottery_code BIGINT NOT NULL, button_index INTEGER NOT NULL,
    period BIGINT NOT NULL, used_count INTEGER NOT NULL CHECK (used_count >= 0),
    total_count INTEGER NOT NULL CHECK (total_count >= used_count),
    PRIMARY KEY (player_id, lottery_code, button_index)
);
CREATE TABLE public.lottery_bonus_receipts (
    player_id TEXT NOT NULL REFERENCES public.players(player_id) ON DELETE CASCADE,
    bonus_code BIGINT NOT NULL, setting_index INTEGER NOT NULL,
    cycle BIGINT NOT NULL CHECK (cycle >= 0), reward_point BIGINT NOT NULL,
    received_at BIGINT NOT NULL,
    PRIMARY KEY (player_id, bonus_code, setting_index, cycle, reward_point)
);
CREATE TABLE public.lottery_histories (
    id BIGSERIAL PRIMARY KEY,
    player_id TEXT NOT NULL REFERENCES public.players(player_id) ON DELETE CASCADE,
    operation_key TEXT NOT NULL, lottery_code BIGINT NOT NULL,
    button_index INTEGER, exec_at BIGINT NOT NULL,
    consume_item_code BIGINT NOT NULL, consume_count INTEGER NOT NULL CHECK (consume_count >= 0),
    details JSONB NOT NULL, probability_hash TEXT,
    UNIQUE (player_id, operation_key)
);
CREATE INDEX lottery_histories_player_time ON public.lottery_histories(player_id, exec_at DESC, id DESC);
