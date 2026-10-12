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
