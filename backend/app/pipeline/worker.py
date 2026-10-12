import shutil, threading, traceback, logging, wave
from io import BytesIO
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from ..core.config import settings
from ..db.repository import get_job, update_job
from .audio import normalize_audio, duration
from .models import save_segments, load_segments
from .merge import merge_speakers
from .export import export_all
from ..providers.asr import get_asr_provider
from ..providers.diarization import get_diarization_provider
from ..providers.llm import LLMProvider

class JobWorker:
    def __init__(self):
        self.executor=ThreadPoolExecutor(max_workers=settings.max_workers)
        self.cancelled=set(); self.lock=threading.Lock()
    def submit(self,job_id): self.executor.submit(self.run,job_id)
    def cancel(self,job_id):
        with self.lock: self.cancelled.add(job_id)
    def _cancel(self,job_id):
        with self.lock: return job_id in self.cancelled
    def run(self,job_id):
        logging.info('Job %s: run() invoked', job_id)
        job=get_job(job_id)
        if not job: return
        root=settings.root/'jobs'/job_id; root.mkdir(parents=True,exist_ok=True)
        try:
            update_job(job_id,status='running',step='prepare',progress=0,error=None)
            logging.info('Job %s: preparing', job_id)
            src=Path(job['source_path']); audio=root/'audio'/'normalized.wav'
            normalize_audio(src,audio)
            logging.info('Job %s: normalized audio created at %s', job_id, audio)
            dur=duration(audio); update_job(job_id,duration=dur)
            logging.info('Job %s: duration=%s', job_id, dur)
            if self._cancel(job_id): return self._finish_cancel(job_id)

            asr_file=root/'asr'/'transcript.json'
            if asr_file.exists(): asr=load_segments(asr_file)
            else:
                update_job(job_id,step='asr',progress=5)
                logging.info('Job %s: starting ASR', job_id)
                provider=get_asr_provider()
                def prog(sec):
                    p=5 + min(60, (sec/dur*60 if dur else 0))
                    update_job(job_id,progress=p)
                asr=provider.transcribe(audio,prog); save_segments(asr_file,asr)
                logging.info('Job %s: ASR finished, %d segments', job_id, len(asr) if hasattr(asr, '__len__') else 0)
            if self._cancel(job_id): return self._finish_cancel(job_id)

            sp_file=root/'diarization'/'speakers.json'
            if sp_file.exists(): speakers=load_segments(sp_file)
            elif settings.diarization_provider.lower()=='none': speakers=[]; save_segments(sp_file,speakers)
            else:
                update_job(job_id,step='diarization',progress=65)
                logging.info('Job %s: starting diarization', job_id)
                speakers=get_diarization_provider().diarize(audio); save_segments(sp_file,speakers)
                logging.info('Job %s: diarization finished, %d speakers', job_id, len(speakers) if hasattr(speakers, '__len__') else 0)
            merged=merge_speakers(asr,speakers) if speakers else asr
            merged_file=root/'merged'/'timeline.json'; save_segments(merged_file,merged)
            logging.info('Job %s: merged timeline saved %s', job_id, merged_file)

            if self._cancel(job_id): return self._finish_cancel(job_id)
            update_job(job_id,step='llm',progress=75)
            logging.info('Job %s: starting LLM step', job_id)
            if settings.llm_enabled:
                merged=LLMProvider().translate(merged)
                save_segments(merged_file,merged)
                logging.info('Job %s: LLM translate finished', job_id)

            update_job(job_id,step='export',progress=92)
            logging.info('Job %s: starting export', job_id)
            title=Path(job['filename']).stem.replace('/','_')
            export_all(root/'output',merged,title)
            logging.info('Job %s: export completed', job_id)
            update_job(job_id,status='done',step='done',progress=100)
            logging.info('Job %s: finished successfully', job_id)
        except Exception as e:
            # capture full traceback and save into DB and logs
            tb = traceback.format_exc()
            logging.exception('Job %s failed', job_id)
            # store traceback (may be long) into error field
            try:
                update_job(job_id, status='failed', step='error', error=tb)
            except Exception:
                logging.exception('Failed to update job error field for %s', job_id)
            # generate a 1-second silent WAV as an error audio fallback
            try:
                out_dir = (settings.root / 'jobs' / job_id / 'output')
                out_dir.mkdir(parents=True, exist_ok=True)
                err_path = out_dir / 'error.wav'
                # 1 second of silence, 16kHz, mono, 16-bit
                with wave.open(str(err_path), 'wb') as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(16000)
                    wf.writeframes(b'\x00' * 16000 * 2)
            except Exception:
                logging.exception('Failed to create error audio for %s', job_id)
    def _finish_cancel(self,job_id): update_job(job_id,status='cancelled',step='cancelled')

worker=JobWorker()
