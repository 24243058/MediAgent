"""
MediAgent — Backend Entrypoint

Run with: uvicorn backend.main:app --reload
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes import router
from backend.config import settings

app = FastAPI(title=settings.APP_NAME, description=settings.APP_TAGLINE)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten for production
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")


@app.get("/")
def root():
    return {"app": settings.APP_NAME, "tagline": settings.APP_TAGLINE}
