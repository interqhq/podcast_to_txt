from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[3]

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(ROOT / '.env'), extra='ignore')
    host: str = '127.0.0.1'
    port: int = 8765
    data_dir: str = str(ROOT / 'data')
    asr_provider: str = 'faster_whisper'
    asr_model: str = 'large-v3-turbo'
    asr_language: str | None = 'en'
    asr_device: str = 'auto'
    asr_compute_type: str = 'auto'
    asr_beam_size: int = 5
    asr_vad_filter: bool = True
    diarization_provider: str = 'none'
    diarization_model: str = 'pyannote/speaker-diarization-community-1'
    hf_token: str = ''
    llm_enabled: bool = False
    llm_provider: str = 'deepseek'
    llm_base_url: str = 'https://api.deepseek.com'
    llm_api_key: str = ''
    llm_model: str = 'deepseek-chat'
    llm_target_language: str = 'zh-CN'
    llm_chunk_chars: int = 9000
    worker_poll_seconds: float = 2.0
    max_workers: int = 1
    global_json_export_dir: str = ''

    @property
    def root(self) -> Path:
        return Path(self.data_dir)

    def ensure_dirs(self):
        for p in [self.root, self.root/'uploads', self.root/'jobs', self.root/'models']:
            p.mkdir(parents=True, exist_ok=True)
        if self.global_json_export_dir.strip():
            Path(self.global_json_export_dir).expanduser().mkdir(parents=True, exist_ok=True)

    @property
    def global_json_export_path(self) -> Path | None:
        path = self.global_json_export_dir.strip()
        if not path:
            return None
        return Path(path).expanduser()

settings = Settings()
settings.ensure_dirs()
