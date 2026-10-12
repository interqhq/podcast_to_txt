from datetime import datetime, timezone
import logging
from .database import db

def now(): return datetime.now(timezone.utc).isoformat()

def create_job(job_id, filename, source_path):
    t=now()
    with db() as con:
        con.execute('INSERT INTO jobs(id,filename,source_path,status,step,progress,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)',
                    (job_id, filename, source_path, 'queued', 'queued', 0, t, t))

def get_job(job_id):
    with db() as con:
        r=con.execute('SELECT * FROM jobs WHERE id=?',(job_id,)).fetchone()
        return dict(r) if r else None

def list_jobs(limit=100):
    with db() as con:
        return [dict(r) for r in con.execute('SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?', (limit,)).fetchall()]

def update_job(job_id, **fields):
    fields['updated_at']=now()
    cols=', '.join(f'{k}=?' for k in fields)
    with db() as con:
        con.execute(f'UPDATE jobs SET {cols} WHERE id=?', (*fields.values(), job_id))
    logging.debug('update_job %s %s', job_id, fields)

def delete_job(job_id):
    with db() as con:
        con.execute('DELETE FROM jobs WHERE id=?', (job_id,))
