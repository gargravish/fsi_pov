"""UBS Helix — FastAPI application entrypoint."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .routers.api import router as api_router

app = FastAPI(title="UBS Helix API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/healthz")
def healthz():
    return {"status": "ok", "use_bq": settings.USE_BQ,
            "project": settings.GOOGLE_CLOUD_PROJECT, "dataset": settings.BQ_DATASET}
