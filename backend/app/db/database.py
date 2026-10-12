import sqlite3
from pathlib import Path
from contextlib import contextmanager
from ..core.config import settings

DB_PATH = settings.root / 'podcast_studio.db'

SCHEMA = '''
CREATE TABLE IF NOT EXISTS jobs (
 id TEXT PRIMARY KEY,
 filename TEXT NOT NULL,
 source_path TEXT NOT NULL,
 status TEXT NOT NULL,
 step TEXT NOT NULL,
 progress REAL NOT NULL DEFAULT 0,
 error TEXT,
 created_at TEXT NOT NULL,
 updated_at TEXT NOT NULL,
 duration REAL,
 title TEXT
);
CREATE INDEX IF NOT EXISTS idx_jobs_created ON jobs(created_at DESC);
'''

def init_db():
    with sqlite3.connect(DB_PATH) as con:
        con.executescript(SCHEMA)
        con.commit()

@contextmanager
def db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    finally:
        con.close()
