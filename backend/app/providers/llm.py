import json, re, httpx
from ..core.config import settings
from ..pipeline.models import Segment

SYSTEM='''You are a professional podcast transcript editor. Translate English podcast transcript segments into natural Simplified Chinese. Preserve meaning, names, technical terms and speaker boundaries. Return ONLY a JSON array. Each item must contain id and translated. Do not add commentary.'''

class LLMProvider:
    def __init__(self):
        self.url=settings.llm_base_url.rstrip('/') + '/chat/completions'
    def enabled(self): return settings.llm_enabled and bool(settings.llm_api_key)
    def translate(self, segments):
        if not self.enabled(): return segments
        chunks=[]; cur=[]; chars=0
        for i,s in enumerate(segments):
            n=len(s.text)
            if cur and chars+n>settings.llm_chunk_chars:
                chunks.append(cur); cur=[]; chars=0
            cur.append((i,s)); chars+=n
        if cur: chunks.append(cur)
        with httpx.Client(timeout=180) as client:
            for chunk in chunks:
                payload=[{'id':i,'speaker':s.speaker or 'SPEAKER_00','text':s.text} for i,s in chunk]
                r=client.post(self.url,headers={'Authorization':f'Bearer {settings.llm_api_key}','Content-Type':'application/json'},json={
                    'model':settings.llm_model,'temperature':0.1,
                    'messages':[{'role':'system','content':SYSTEM},{'role':'user','content':json.dumps(payload,ensure_ascii=False)}],
                    'response_format':{'type':'json_object'}
                })
                r.raise_for_status(); content=r.json()['choices'][0]['message']['content']
                data=self._parse(content)
                mapping={int(x['id']):x.get('translated','') for x in data if isinstance(x,dict) and str(x.get('id','')).isdigit()}
                for i,s in chunk: s.translated=mapping.get(i,s.translated)
        return segments
    def _parse(self,content):
        obj=json.loads(content)
        if isinstance(obj,list): return obj
        for k in ('items','segments','data','translations'):
            if isinstance(obj.get(k),list): return obj[k]
        m=re.search(r'\[[\s\S]*\]',content)
        return json.loads(m.group(0)) if m else []
