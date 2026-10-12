from pathlib import Path
import json
from .models import Segment

def ts_srt(x):
    ms=int(round(x*1000)); h=ms//3600000; ms%=3600000; m=ms//60000; ms%=60000; s=ms//1000; ms%=1000
    return f'{h:02d}:{m:02d}:{s:02d},{ms:03d}'

def export_all(out: Path, segments: list[Segment], title: str):
    out.mkdir(parents=True, exist_ok=True)
    raw=[s.to_dict() for s in segments]
    (out/f'{title}.json').write_text(json.dumps(raw,ensure_ascii=False,indent=2),encoding='utf-8')
    md=[]; txt=[]; srt=[]
    for i,s in enumerate(segments,1):
        who=s.speaker or 'SPEAKER_00'
        zh=s.translated or ''
        line=f'**{who}**  \n{s.text}' + (f'\n\n> {zh}' if zh else '')
        md.append(line); txt.append(f'{who}: {s.text}' + (f'\n中文：{zh}' if zh else ''))
        srt.append(f'{i}\n{ts_srt(s.start)} --> {ts_srt(s.end)}\n{zh or s.text}\n')
    (out/f'{title}.md').write_text('\n\n'.join(md),encoding='utf-8')
    (out/f'{title}.txt').write_text('\n\n'.join(txt),encoding='utf-8')
    (out/f'{title}.srt').write_text('\n'.join(srt),encoding='utf-8')
