# Modified for POV+ by kudykam · 2026-10-30 · GPL-3.0-only
"""Small separate metadata cache; no playback URLs or credentials."""
import json
import sqlite3
import time
from pathlib import Path


class Store:
    def __init__(self, path):
        self.path = str(path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY,payload TEXT NOT NULL,expires REAL NOT NULL)')

    def connect(self):
        return sqlite3.connect(self.path, timeout=15)

    def get(self, key, allow_stale=False):
        with self.connect() as db:
            row = db.execute('SELECT payload,expires FROM cache WHERE key=?',(key,)).fetchone()
        if not row or (row[1] < time.time() and not allow_stale):
            return None
        return json.loads(row[0])

    def put(self, key, data, ttl=3600):
        with self.connect() as db:
            db.execute('INSERT INTO cache VALUES(?,?,?) ON CONFLICT(key) DO UPDATE SET payload=excluded.payload,expires=excluded.expires',
                       (key,json.dumps(data,ensure_ascii=False),time.time()+ttl))
