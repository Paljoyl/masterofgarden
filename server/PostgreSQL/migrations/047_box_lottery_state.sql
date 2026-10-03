-- NULL means no identity-bound initial state has been imported yet.
-- [] is an explicit current state and must not be replaced by later captures.
ALTER TABLE public.players ADD COLUMN box_lotteries JSONB;
ALTER TABLE public.players ADD CONSTRAINT player_box_lotteries_array CHECK (
    box_lotteries IS NULL OR jsonb_typeof(box_lotteries) = 'array'
);
