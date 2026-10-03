"""Player-owned magic item grants composed inside the player's transaction."""


class MagicItemStore:
    def __init__(self, repository):
        self.repo = repository
        self.connection = repository.connection

    def grant(self, player_id, code, now):
        created = bool(self.connection.execute('''INSERT INTO public.magic_items
            (player_id,magic_item_code,level,created_at) VALUES (%s,%s,1,%s)
            ON CONFLICT DO NOTHING RETURNING magic_item_code''', (player_id, code, now)).fetchone())
        if created:
            self.repo._touch(player_id)
        return created

    def levelup(self, player_id, code, previous_level, target_level):
        from .players import OperationConflict
        updated = self.connection.execute('''UPDATE public.magic_items SET level=%s
            WHERE player_id=%s AND magic_item_code=%s AND level=%s
            RETURNING magic_item_code''', (target_level, player_id, code, previous_level)).fetchone()
        if updated is None:
            raise OperationConflict('Magic item level changed')
        self.repo._touch(player_id)
