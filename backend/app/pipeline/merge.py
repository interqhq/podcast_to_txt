from .models import Segment

def overlap(a,b):
    return max(0.0, min(a.end,b.end)-max(a.start,b.start))

def merge_speakers(asr, speakers):
    out=[]
    for seg in asr:
        best=None; score=0
        for sp in speakers:
            x=overlap(seg, sp)
            if x>score: score=x; best=sp
        seg.speaker = best.speaker if best else 'SPEAKER_00'
        out.append(seg)
    return out
