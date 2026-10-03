-- Explicit local-server odds, not an official probability capture.
-- Keep existing player balances, counters and lottery history unchanged.
INSERT INTO public.lottery_definitions (name, data) VALUES
('local_lottery_probability_master', $local$[
  {
    "Code": 10000001,
    "Distribution": "uniform-within-rarity",
    "RarityChanceA": ["79", "18", "3"],
    "RarityChanceB": ["0", "97", "3"],
    "Source": "Local configuration for the permanent regular pool; official odds unavailable."
  }
]$local$::jsonb)
ON CONFLICT (name) DO NOTHING;
