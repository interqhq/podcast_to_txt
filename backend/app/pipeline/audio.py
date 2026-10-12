import subprocess, json
from pathlib import Path

def normalize_audio(src: Path, dst: Path):
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() and dst.stat().st_size > 0: return
    cmd=['ffmpeg','-y','-i',str(src),'-vn','-ac','1','-ar','16000','-c:a','pcm_s16le',str(dst)]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

def duration(path: Path) -> float | None:
    try:
        p=subprocess.run(['ffprobe','-v','error','-show_entries','format=duration','-of','json',str(path)], capture_output=True, text=True, check=True)
        return float(json.loads(p.stdout)['format']['duration'])
    except Exception:
        return None
