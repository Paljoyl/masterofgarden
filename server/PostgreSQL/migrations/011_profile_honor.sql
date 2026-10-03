-- NULL keeps the identity-bound profile seed until the first local selection.
-- Zero explicitly clears the selection; positive values identify an owned honor.
ALTER TABLE public.players
    ADD COLUMN profile_honor_code BIGINT CHECK (profile_honor_code >= 0);
