from pathlib import Path
from ..core.config import settings
from ..pipeline.models import Segment

class FasterWhisperProvider:
    def __init__(self): self.model=None
    def load(self):
        if self.model: return
        from faster_whisper import WhisperModel
        device=settings.asr_device
        if device=='auto': device='cuda' if self._cuda_available() else 'cpu'
        ct=settings.asr_compute_type
        if ct=='auto':
            ct='float16' if device=='cuda' else 'int8'
        # Some CPU backends do not support float16 efficiently.
        # Fall back to int8 for CPU to keep the model loadable.
        if device == 'cpu' and ct in {'float16', 'float32'}:
            ct = 'int8'
        try:
            self.model=WhisperModel(settings.asr_model, device=device, compute_type=ct)
        except ValueError as exc:
            if device == 'cpu' and 'float16' in str(exc):
                self.model=WhisperModel(settings.asr_model, device='cpu', compute_type='int8')
            else:
                raise
    def _cuda_available(self):
        try:
            import torch; return bool(torch.cuda.is_available())
        except Exception: return False
    def transcribe(self, audio: Path, progress=None):
        self.load()
        kwargs={'beam_size':settings.asr_beam_size,'vad_filter':settings.asr_vad_filter}
        if settings.asr_language: kwargs['language']=settings.asr_language
        segments, info=self.model.transcribe(str(audio), **kwargs)
        result=[]
        for x in segments:
            text=(x.text or '').strip()
            if not text: continue
            result.append(Segment(start=float(x.start),end=float(x.end),text=text,language=getattr(info,'language',None),confidence=None))
            if progress: progress(float(x.end))
        return result

class FunASRProvider:
    def __init__(self): self.model=None
    def load(self):
        if self.model: return
        from funasr import AutoModel
        device='cuda' if settings.asr_device=='cuda' else ('cuda' if self._cuda() and settings.asr_device=='auto' else 'cpu')
        self.model=AutoModel(model=settings.asr_model, device=device, disable_update=True)
    def _cuda(self):
        try:
            import torch; return torch.cuda.is_available()
        except Exception: return False
    def transcribe(self,audio:Path,progress=None):
        self.load()
        res=self.model.generate(input=str(audio), batch_size_s=300)
        if isinstance(res,dict): res=[res]
        out=[]
        for item in res:
            text=item.get('text','').strip()
            if not text: continue
            # FunASR output varies by model; preserve full text as one segment if no timestamps.
            ts=item.get('timestamp') or item.get('timestamps')
            if ts:
                for t in ts:
                    if len(t)>=2: out.append(Segment(t[0]/1000,t[1]/1000,text,''))
            else: out.append(Segment(0,0,text))
        return out

def get_asr_provider():
    if settings.asr_provider.lower()=='funasr': return FunASRProvider()
    return FasterWhisperProvider()
