"""Persist server-issued local session digests without retaining credentials."""


class SessionStore:
    def __init__(self, repository):
        self.repo = repository

    def save(self, digest, player_id, variant, issued_at, expires_at):
        with self.repo.lock, self.repo.connection.transaction():
            self.repo.connection.execute('''INSERT INTO public.player_sessions
                (token_hash,player_id,variant,issued_at,expires_at) VALUES (%s,%s,%s,%s,%s)''',
                (digest, player_id, variant, issued_at, expires_at))

    def load(self, digest, variant, now):
        with self.repo.lock:
            return self.repo.connection.execute('''SELECT player_id,variant,expires_at FROM public.player_sessions
                WHERE token_hash=%s AND variant=%s AND expires_at>%s''', (digest, variant, now)).fetchone()
