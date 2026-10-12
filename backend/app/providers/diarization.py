from pathlib import Path
from ..core.config import settings
from ..pipeline.models import Segment

class NoneDiarization:
    def diarize(self,audio): return []

class FunASRCamDiarization:
    def __init__(self): self.model=None
    def load(self):
        if self.model: return
        from funasr import AutoModel
        device='cuda' if self._cuda() and settings.asr_device!='cpu' else 'cpu'
        self.model=AutoModel(model=settings.asr_model if settings.asr_provider=='funasr' else 'iic/SenseVoiceSmall',
                             vad_model='fsmn-vad', spk_model='cam++', device=device, disable_update=True)
    def _cuda(self):
        try:
            import torch; return torch.cuda.is_available()
        except Exception: return False
    def diarize(self,audio):
        self.load(); res=self.model.generate(input=str(audio), batch_size_s=300)
        if not res: return []
        info=res[0].get('sentence_info',[]) if isinstance(res,list) else res.get('sentence_info',[])
        out=[]
        for x in info:
            if x.get('spk') is None: continue
            out.append(Segment(float(x.get('start',0))/1000,float(x.get('end',0))/1000,'',f'SPEAKER_{int(x["spk"]):02d}'))
        return out

class PyannoteDiarization:
    def __init__(self): self.pipeline=None
    def load(self):
        if self.pipeline: return
        if not settings.hf_token: raise RuntimeError('HF_TOKEN is required for pyannote')
        from pyannote.audio import Pipeline
        self.pipeline=Pipeline.from_pretrained(settings.diarization_model, token=settings.hf_token)
        try:
            import torch
            if torch.cuda.is_available(): self.pipeline.to(torch.device('cuda'))
        except Exception: pass
    def diarize(self,audio):
        self.load(); ann=self.pipeline(str(audio))
        out=[]
        # pyannote versions expose itertracks in the standard Annotation API.
        for turn,_,speaker in ann.itertracks(yield_label=True):
            out.append(Segment(float(turn.start),float(turn.end),'',speaker=str(speaker)))
        return out

def get_diarization_provider():
    p=settings.diarization_provider.lower()
    if p=='pyannote': return PyannoteDiarization()
    if p in ('funasr_campp','cam++','campp'): return FunASRCamDiarization()
    return NoneDiarization()
