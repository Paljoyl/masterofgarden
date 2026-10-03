-- Keep the home aggregate in the local schema so public remains the stable
-- 17-table player model. Existing installs are migrated without losing state.
CREATE TABLE IF NOT EXISTS mog_local.player_home_state (
    player_id TEXT PRIMARY KEY REFERENCES public.players ON DELETE CASCADE,
    character_costume_code BIGINT NOT NULL CHECK (character_costume_code >= 0),
    situations JSONB NOT NULL CHECK (jsonb_typeof(situations) = 'array'),
    home_characters JSONB NOT NULL CHECK (jsonb_typeof(home_characters) = 'array'),
    quiz_answers JSONB NOT NULL CHECK (jsonb_typeof(quiz_answers) = 'array')
);
INSERT INTO mog_local.player_home_state
    (player_id, character_costume_code, situations, home_characters, quiz_answers)
SELECT player_id, character_costume_code, situations, home_characters, quiz_answers
FROM public.player_home_state
ON CONFLICT (player_id) DO NOTHING;
DROP TABLE public.player_home_state;
