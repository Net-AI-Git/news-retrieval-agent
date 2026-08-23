import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src.config import api_settings
from src.routes import api, docs

app = FastAPI(**api_settings.model_dump(exclude={"prefix": True}))

app.include_router(api.api_router, prefix=api_settings.prefix)
app.include_router(docs.router)
app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
