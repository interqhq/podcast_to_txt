from dataclasses import dataclass, asdict
from typing import Optional
import json

@dataclass
class Segment:
    start: float
    end: float
    text: str
    speaker: Optional[str] = None
    language: Optional[str] = None
    confidence: Optional[float] = None
    translated: Optional[str] = None

    def to_dict(self): return asdict(self)

def save_segments(path, segments):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps([s.to_dict() for s in segments], ensure_ascii=False, indent=2), encoding='utf-8')

def load_segments(path):
    data=json.loads(path.read_text(encoding='utf-8'))
    return [Segment(**x) for x in data]
