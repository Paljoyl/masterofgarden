-- Current home selection and owned home progress, separate from captured responses.
CREATE TABLE public.player_home_state (
    player_id TEXT PRIMARY KEY REFERENCES public.players ON DELETE CASCADE,
    character_costume_code BIGINT NOT NULL CHECK (character_costume_code >= 0),
    situations JSONB NOT NULL CHECK (jsonb_typeof(situations) = 'array'),
    home_characters JSONB NOT NULL CHECK (jsonb_typeof(home_characters) = 'array'),
    quiz_answers JSONB NOT NULL CHECK (jsonb_typeof(quiz_answers) = 'array')
);
