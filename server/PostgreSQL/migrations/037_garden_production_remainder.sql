-- Preserve fractional production and unconverted points when changing workers or targets.
ALTER TABLE public.player_garden_buildings
    ADD COLUMN stored_volume NUMERIC NOT NULL DEFAULT 0 CHECK (stored_volume >= 0);
