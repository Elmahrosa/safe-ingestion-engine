"""
api/server.py — Safe Ingestion Engine · single app entrypoint
=============================================================
Run with:
    python -m uvicorn api.server:app --host 0.0.0.0 --port 8000 --reload

Production (Docker):
    CMD ["uvicorn", "api.server:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
"""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes.ingest  import router as ingest_router
from api.routes.metrics import router as metrics_router

VERSION = open("VERSION").read().strip() if os.path.exists("VERSION") else "1.0.0"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    yield
    # shutdown — nothing to clean up yet


app = FastAPI(
    title="Safe Ingestion Engine",
    description=(
        "PII-scrubbing URL ingestion API. "
        "Authenticate with `X-API-Key: sk-safe-XXXXXXXXXX`."
    ),
    version=VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://safe.teosegypt.com"],
    allow_methods=["GET", "POST"],
    allow_headers=["X-API-Key", "Content-Type"],
)

# ── Routers ────────────────────────────────────────────────────────────────────
app.include_router(ingest_router)
app.include_router(metrics_router)


# ── Health ─────────────────────────────────────────────────────────────────────
@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok", "version": VERSION}
