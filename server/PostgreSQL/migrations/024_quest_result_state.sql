-- Add retry-safe settlement to existing battles; preserve every player/session.
ALTER TABLE public.quest_sessions ADD COLUMN result_hash TEXT;
ALTER TABLE public.quest_sessions ADD COLUMN result_response BYTEA;
ALTER TABLE public.quest_sessions ADD CONSTRAINT quest_session_result_pair
    CHECK ((result_hash IS NULL) = (result_response IS NULL));
