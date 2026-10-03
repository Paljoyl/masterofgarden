-- Local simulation policy for pools lacking usable official odds.
-- Existing per-pool overrides and saved player state are preserved.
INSERT INTO public.lottery_definitions (name, data) VALUES
('local_lottery_probability_policy', $local$[
  {
    "Enabled": true,
    "RarityChanceA": ["79", "18", "3"],
    "RarityChanceB": ["0", "97", "3"],
    "PickupShares": {"1": "0.46", "2": "0.23"},
    "Source": "Explicit local simulation defaults. Valid exact-pool official caches take precedence; these defaults are not official odds."
  }
]$local$::jsonb)
ON CONFLICT (name) DO NOTHING;

CREATE TABLE public.player_lottery_selections (
  player_id TEXT NOT NULL REFERENCES public.players(player_id) ON DELETE CASCADE,
  lottery_code BIGINT NOT NULL,
  characters JSONB NOT NULL CHECK (jsonb_typeof(characters) = 'array'),
  updated_at BIGINT NOT NULL,
  PRIMARY KEY (player_id, lottery_code)
);
