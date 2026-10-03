"""Owned battle sessions; called inside the existing player transaction."""
from mog_protocol.codec import decode, encode
from local_server.protocol import LocalError


class QuestStore:
    def __init__(self, repository):
        self.repo = repository
        self.connection = repository.connection

    def previous(self, player_id, unique_id, request_hash):
        row = self.connection.execute('''SELECT request_hash,state,start_response FROM public.quest_sessions
            WHERE player_id=%s AND quest_unique_id=%s''', (player_id, unique_id)).fetchone()
        if row is None:
            return None
        if row[0] != request_hash:
            raise LocalError('local_quest_start_id_conflict', 409)
        if row[1] != 'active':
            raise LocalError('local_quest_session_closed', 409)
        return decode(bytes(row[2]))

    def start(self, player_id, unique_id, quest_code, request_hash, party, response, stamina_cost, now):
        self.connection.execute('''UPDATE public.quest_sessions SET state='abandoned',finished_at=%s
            WHERE player_id=%s AND state='active' ''', (now, player_id))
        self.connection.execute('''INSERT INTO public.quest_sessions
            (player_id,quest_unique_id,quest_code,request_hash,party,start_response,stamina_cost,started_at,state)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,'active')''',
            (player_id, unique_id, quest_code, request_hash, encode(party), encode(response), stamina_cost, now))
        self.repo._touch(player_id)

    def result_session(self, player_id, unique_id, quest_code, request_hash):
        row = self.connection.execute('''SELECT quest_code,state,party,stamina_cost,result_hash,result_response
            FROM public.quest_sessions WHERE player_id=%s AND quest_unique_id=%s''',
            (player_id, unique_id)).fetchone()
        if row is None:
            raise LocalError('local_quest_session_not_found', 409)
        if row[0] != quest_code:
            raise LocalError('local_quest_session_code_mismatch', 409)
        if row[4] is not None:
            if row[4] != request_hash:
                raise LocalError('local_quest_result_id_conflict', 409)
            return decode(bytes(row[2])), row[3], decode(bytes(row[5]))
        if row[1] != 'active':
            raise LocalError('local_quest_session_closed', 409)
        return decode(bytes(row[2])), row[3], None

    def finish(self, player_id, unique_id, request_hash, response, now):
        self.connection.execute('''UPDATE public.quest_sessions SET state='settled',finished_at=%s,
            result_hash=%s,result_response=%s WHERE player_id=%s AND quest_unique_id=%s AND state='active' ''',
            (now, request_hash, encode(response), player_id, unique_id))
        self.repo._touch(player_id)
