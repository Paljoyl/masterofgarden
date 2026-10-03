"""Player-owned skill tree state inside the caller's player transaction."""
from psycopg.types.json import Jsonb

from .player_protocol import InvalidPlayerData, collection, integer, record


class SkillTreeStore:
    def __init__(self, repository):
        self.repo, self.connection = repository, repository.connection

    def get(self, player_id):
        row = self.connection.execute('''SELECT node_infos,floor_complete_infos
            FROM public.player_skill_trees WHERE player_id=%s''', (player_id,)).fetchone()
        return list(row) if row is not None else None

    def seed(self, player_id, value=None):
        current = self.get(player_id)
        if current is not None:
            return current
        if value is None:
            value = [[], []]
        tree = record(self.repo.registry, 'SkillTreeInfo', value)
        collections = []
        for field, model, code_field in (('NodeInfos', 'SkillTreeNodeInfo', 'NodeCode'),
                                        ('FloorCompleteInfos', 'SkillTreeFloorCompleteInfo', 'FloorCode')):
            entries, seen = [], set()
            for entry in collection(tree[field] or [], field):
                row = record(self.repo.registry, model, entry)
                code = integer(row[code_field], code_field)
                level = integer(row['Level'], 'Level')
                if code <= 0 or code in seen or not 0 <= level <= 255:
                    raise InvalidPlayerData('Invalid skill tree seed')
                seen.add(code)
                entries.append([code, level])
            collections.append(sorted(entries))
        self.connection.execute('''INSERT INTO public.player_skill_trees
            (player_id,node_infos,floor_complete_infos) VALUES (%s,%s,%s)
            ON CONFLICT (player_id) DO NOTHING''',
            (player_id, Jsonb(collections[0]), Jsonb(collections[1])))
        return self.get(player_id)

    def save(self, player_id, nodes, floors):
        self.connection.execute('''UPDATE public.player_skill_trees
            SET node_infos=%s,floor_complete_infos=%s WHERE player_id=%s''',
            (Jsonb([[code, level] for code, level in sorted(nodes.items())]),
             Jsonb([[code, level] for code, level in sorted(floors.items())]), player_id))
        self.repo._touch(player_id)
