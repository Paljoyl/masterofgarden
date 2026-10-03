"""Public starter rewards matching the original project's 16 pending presents."""
from hashlib import sha256
import json

from mog_protocol.codec import encode


# Reward definitions only: no original player IDs, present IDs or receipt state.
STARTER_PRESENTS = (
    ("事前登錄200,000人里程碑達成獎勵", 990000001, 500),
    ("謝謝各位玩家支持！", 990000001, 600),
    ("事前登錄700,000人里程碑達成獎勵", 990000001, 1000),
    ("事前登錄200,000人里程碑達成獎勵", 310000004, 20),
    ("事前登錄400,000人里程碑達成獎勵", 990000001, 500),
    ("DC各式慶祝活動展開中!詳情請至官方DC!", 390000003, 5),
    ("新手限定闇影慶典招待券", 900000021, 1),
    ("事前登錄30,000人里程碑達成獎勵", 990000001, 200),
    ("事前登錄1,000,000人里程碑達成獎勵", 990000001, 1000),
    ("事前登錄400,000人里程碑達成獎勵", 310000004, 30),
    ("事前登錄1,000,000人里程碑達成獎勵", 900000001, 10),
    ("來自營運的小禮物", 990000001, 3500),
    ("雙平台預註冊獎勵", 990000001, 1000),
    ("事前登錄50,000人里程碑達成獎勵", 990000001, 300),
    ("雙平台預註冊獎勵", 900000001, 10),
    ("事前登錄100,000人里程碑達成獎勵", 990000001, 500),
)


def grant_starter_presents(repository, player_id, now):
    """Compose with account creation; rewards remain unclaimed until box receipt."""
    for index, (message, code, amount) in enumerate(STARTER_PRESENTS):
        # New, player-specific 16-byte ULIDs; retries retain the same grant identity.
        present_id = (now * 1000).to_bytes(6, "big") + sha256(
            encode(["standalone-starter-presents-v1", player_id, index])).digest()[:10]
        title = json.dumps({"ReplaceMessage": {
            "DirectMessage": {"Jp": None, "EnUs": None, "ZhTw": message, "KoKr": None},
            "Reference": None, "ReplaceMessages": None}}, separators=(",", ":"))
        repository.add_present(player_id, present_id, title=title, inventory_type=2,
            inventory_code=code, amount=amount, sender_icon_code=1000000,
            arrived_at=now, limit_date=None)
