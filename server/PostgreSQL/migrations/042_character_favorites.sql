-- NULL marks an existing player whose favorites have not been seeded yet.
-- An empty array is an explicit saved state and must never be reseeded.
ALTER TABLE public.players ADD COLUMN favorite_character_codes BIGINT[];
ALTER TABLE public.players ADD CONSTRAINT player_favorite_codes_valid CHECK (
    favorite_character_codes IS NULL OR (
        array_position(favorite_character_codes, NULL) IS NULL
        AND 0 < ALL(favorite_character_codes)
    )
);
