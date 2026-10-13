# main.py 最顶部
import os

def _fix_proxy_env():
    for k in ("ALL_PROXY", "all_proxy", "HTTP_PROXY", "http_proxy",
              "HTTPS_PROXY", "https_proxy"):
        v = os.environ.get(k)
        if v and v.startswith("socks://"):
            os.environ[k] = "http://" + v[len("socks://"):]

_fix_proxy_env()


os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"


from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from .core.config import settings
from .db.database import init_db
from .api.routes import router

init_db()
app=FastAPI(title='Podcast Studio V1',version='1.0.0')
app.add_middleware(CORSMiddleware,allow_origins=['*'],allow_methods=['*'],allow_headers=['*'])
app.include_router(router)
frontend=Path(__file__).resolve().parents[2]/'frontend'/'dist'
if frontend.exists():
    app.mount('/',StaticFiles(directory=frontend,html=True),name='frontend')
else:
    @app.get('/')
    def root(): return {'name':'Podcast Studio V1','docs':'/docs'}
