-- Current player-owned climbing entry state; existing player progress is preserved.
CREATE TABLE public.player_climbing_state (
    player_id TEXT PRIMARY KEY REFERENCES public.players(player_id) ON DELETE CASCADE,
    matching_enemies JSONB NOT NULL DEFAULT '[]'::jsonb
        CHECK (jsonb_typeof(matching_enemies) = 'array'),
    clear_floor INTEGER NOT NULL DEFAULT 0 CHECK (clear_floor >= 0),
    floor_battle_index INTEGER NOT NULL DEFAULT 0 CHECK (floor_battle_index >= 0),
    character_statuses JSONB NOT NULL DEFAULT '[]'::jsonb
        CHECK (jsonb_typeof(character_statuses) = 'array'),
    rematching_count INTEGER NOT NULL DEFAULT 0 CHECK (rematching_count >= 0),
    rental_character_statuses JSONB NOT NULL DEFAULT '[]'::jsonb
        CHECK (jsonb_typeof(rental_character_statuses) = 'array'),
    received_reward_floor INTEGER NOT NULL DEFAULT 0 CHECK (received_reward_floor >= 0),
    before_clear_floor INTEGER NOT NULL DEFAULT 0 CHECK (before_clear_floor >= 0)
);
