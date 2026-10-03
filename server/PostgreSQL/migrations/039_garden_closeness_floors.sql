-- Garden mission closeness rights survive acquiring the home character later.
CREATE TABLE public.player_garden_closeness_floors (
    player_id TEXT NOT NULL REFERENCES public.players(player_id) ON DELETE CASCADE,
    home_character_code BIGINT NOT NULL,
    level INTEGER NOT NULL CHECK (level > 0),
    PRIMARY KEY (player_id,home_character_code)
);
