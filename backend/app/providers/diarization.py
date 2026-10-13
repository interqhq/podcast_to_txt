from pathlib import Path
from ..core.config import settings
from ..pipeline.models import Segment


# import os

# # 修复 socks:// 这种 httpx 不认识的协议
# for _k in ("ALL_PROXY", "all_proxy", "HTTP_PROXY", "http_proxy", "HTTPS_PROXY", "https_proxy"):
#     _v = os.environ.get(_k)
#     if _v and _v.startswith("socks://"):
#         os.environ[_k] = "http://" + _v[len("socks://"):]

import huggingface_hub as _hfh

# 兼容性补丁：将 use_auth_token 转换为 token
_orig_hf_download = _hfh.hf_hub_download
def _compat_hf_download(*args, **kwargs):
    if "use_auth_token" in kwargs:
        kwargs["token"] = kwargs.pop("use_auth_token")
    return _orig_hf_download(*args, **kwargs)
_hfh.hf_hub_download = _compat_hf_download

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
    # def load(self):
    #     if self.pipeline: return
    #     if not settings.hf_token: raise RuntimeError('HF_TOKEN is required for pyannote')
    #     from pyannote.audio import Pipeline
    #     self.pipeline=Pipeline.from_pretrained(settings.diarization_model, use_auth_token=settings.hf_token)
    #     try:
    #         import torch
    #         if torch.cuda.is_available(): self.pipeline.to(torch.device('cuda'))
    #     except Exception: pass
    def load(self):
        if self.pipeline: return
        from pyannote.audio import Pipeline
        cfg = Path(settings.root) / 'speaker' / 'pyannote' / 'speaker-diarization-3.1' / 'config.yaml'
        # 如果你的 data 目录不在 settings.root 下，这里改成实际路径
        if not cfg.exists():
            raise RuntimeError(f'本地 diarization 配置不存在: {cfg}')
        self.pipeline = Pipeline.from_pretrained(str(cfg))
        if self.pipeline is None:
            raise RuntimeError(f'加载失败: {cfg}')
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
