"""One-time import of an identity-bound, unclaimed captured present-box snapshot."""
from hashlib import sha256

from psycopg.types.json import Jsonb

from mog_protocol.codec import encode
from .player_protocol import InvalidPlayerData, integer


def seed_present_box(repository, player_id, presents, captured_at):
    key = 'capture-present-box:v1'
    captured_at = integer(captured_at, 'present snapshot time')
    with repository.transaction(player_id):
        previous = repository.connection.execute('''SELECT result FROM public.operations
            WHERE player_id=%s AND operation_key=%s''', (player_id, key)).fetchone()
        if previous:
            return 0
        ids = [row['PresentId'] for row in presents]
        if (any(type(value) is not bytes or len(value) != 16 for value in ids)
                or len(ids) != len(set(ids))):
            raise InvalidPlayerData('Invalid captured present IDs')
        existing = {row['present_id'] for row in repository.present_rows(player_id, ids)}
        imported = 0
        for row in presents:
            if row['ReceivedAt'] is not None:
                raise InvalidPlayerData('Captured seed must contain unclaimed presents only')
            if row['PresentId'] in existing:
                continue  # Preserve local contents, expiry and receipt status.
            imported += int(repository.add_present(player_id, row['PresentId'],
                title=row['Title'], inventory_type=row['InventoryType'],
                inventory_code=row['InventoryCode'], amount=row['Amount'],
                sender_icon_code=row['SenderIconCode'], arrived_at=row['ArrivedAt'],
                limit_date=row['LimitDate']))
        result = {'imported': imported, 'preserved': len(existing), 'captured_at': captured_at}
        repository.connection.execute('''INSERT INTO public.operations
            (player_id,operation_key,operation_type,request_hash,result)
            VALUES (%s,%s,'present_seed',%s,%s)''',
            (player_id, key, sha256(encode(presents)).hexdigest(), Jsonb(result)))
        return imported
