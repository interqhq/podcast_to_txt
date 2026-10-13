import shutil, uuid, json, logging
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
import traceback
from ..core.config import settings
from ..db.repository import create_job,get_job,list_jobs,update_job,delete_job
from ..pipeline.worker import worker

router=APIRouter(prefix='/api')
ALLOWED={'.mp3','.m4a','.wav','.flac','.aac','.ogg','.opus','.mp4','.webm'}

@router.get('/config')
def config():
    return {
        'asr_provider':settings.asr_provider,
        'asr_model':settings.asr_model,
        'asr_device':settings.asr_device,
        'diarization_provider':settings.diarization_provider,
        'llm_enabled':settings.llm_enabled,
        'llm_provider':settings.llm_provider,
        'llm_model':settings.llm_model,
        'global_json_export_dir':str(settings.global_json_export_path) if settings.global_json_export_path else '',
    }

@router.post('/jobs')
async def upload_job(file:UploadFile=File(...)):
    ext=Path(file.filename or '').suffix.lower()
    if ext not in ALLOWED: raise HTTPException(400,f'Unsupported audio type: {ext}')
    job_id=uuid.uuid4().hex
    src=settings.root/'uploads'/f'{job_id}{ext}'
    src.parent.mkdir(parents=True, exist_ok=True)
    logging.info('Saving upload to %s', src)
    with src.open('wb') as f:
        while chunk:=await file.read(1024*1024): f.write(chunk)
    create_job(job_id,file.filename, str(src)); worker.submit(job_id)
    logging.info('Created job %s for %s', job_id, file.filename)
    return get_job(job_id)

@router.get('/jobs')
def jobs():
    logging.debug('GET /api/jobs')
    return list_jobs()

@router.get('/jobs/{job_id}')
def job(job_id):
    x=get_job(job_id)
    if not x: raise HTTPException(404)
    return x

@router.post('/jobs/{job_id}/retry')
def retry(job_id):
    x=get_job(job_id)
    if not x: raise HTTPException(404)
    logging.info('Retry requested for job %s', job_id)
    update_job(job_id,status='queued',step='queued',error=None)
    worker.submit(job_id)
    return get_job(job_id)

@router.post('/jobs/{job_id}/cancel')
def cancel(job_id):
    x=get_job(job_id)
    if not x: raise HTTPException(404)
    logging.info('Cancel requested for job %s', job_id)
    worker.cancel(job_id)
    return {'ok':True}

@router.get('/jobs/{job_id}/timeline')
def timeline(job_id):
    x=get_job(job_id)
    if not x: raise HTTPException(404)
    p=settings.root/'jobs'/job_id/'merged'/'timeline.json'
    if not p.exists(): p=settings.root/'jobs'/job_id/'asr'/'transcript.json'
    if not p.exists(): return []
    return json.loads(p.read_text(encoding='utf-8'))

@router.get('/jobs/{job_id}/audio')
def audio(job_id):
    x=get_job(job_id)
    if not x: raise HTTPException(404)
    p=Path(x['source_path'])
    # serve original source if available, otherwise try fallback error audio
    if p.exists():
        return FileResponse(p, media_type='audio/mpeg')
    # fallback to generated error.wav or error.mp3 in output
    out_wav = settings.root/'jobs'/job_id/'output'/'error.wav'
    out_mp3 = settings.root/'jobs'/job_id/'output'/'error.mp3'
    if out_mp3.exists():
        return FileResponse(out_mp3, media_type='audio/mpeg')
    if out_wav.exists():
        return FileResponse(out_wav, media_type='audio/wav')
    raise HTTPException(404)

@router.get('/jobs/{job_id}/files/{name}')
def output_file(job_id,name):
    x=get_job(job_id)
    if not x: raise HTTPException(404)
    p=settings.root/'jobs'/job_id/'output'/name
    if not p.exists() or p.is_dir() or p.name!=name: raise HTTPException(404)
    return FileResponse(p, filename=p.name)

@router.post('/jobs/{job_id}/export-json-global')
def export_json_global(job_id):
    x=get_job(job_id)
    if not x: raise HTTPException(404)
    if x.get('status') != 'done':
        raise HTTPException(409, 'Job is not finished yet')
    export_dir = settings.global_json_export_path
    if export_dir is None:
        raise HTTPException(400, 'GLOBAL_JSON_EXPORT_DIR is not configured')
    title = Path(x['filename']).stem.replace('/','_')
    src = settings.root/'jobs'/job_id/'output'/f'{title}.json'
    if not src.exists():
        raise HTTPException(404, 'Output JSON not found')
    dst = export_dir/f'{title}.json'
    if dst.exists():
        dst = export_dir/f'{title}_{job_id[:8]}.json'
    try:
        shutil.copy2(src, dst)
    except OSError:
        logging.exception('Failed to export json to global dir for job %s', job_id)
        raise HTTPException(500, 'Failed to export json')
    return {'ok': True, 'path': str(dst)}


@router.delete('/jobs/{job_id}')
def delete(job_id):
    x=get_job(job_id)
    if not x: raise HTTPException(404)
    # remove files and DB record
    try:
        job_root = settings.root/'jobs'/job_id
        if job_root.exists():
            shutil.rmtree(job_root)
        # also try to remove uploaded source if present
        src = Path(x.get('source_path') or '')
        if src.exists():
            try:
                src.unlink()
            except Exception:
                logging.exception('Failed to remove source file %s', src)
        delete_job(job_id)
        return {'ok': True}
    except Exception as e:
        logging.exception('Failed to delete job %s', job_id)
        raise HTTPException(500, 'Failed to delete job')


@router.get('/jobs/{job_id}/error')
def job_error(job_id):
    x=get_job(job_id)
    if not x: raise HTTPException(404)
    # return the stored error traceback or message (may be None)
    return {'error': x.get('error')}
