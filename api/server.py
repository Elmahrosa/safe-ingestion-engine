"""
api/server.py — Safe Ingestion Engine · single app entrypoint
=============================================================
Run:
    python -m uvicorn api.server:app --host 0.0.0.0 --port 8000 --reload

Production:
    uvicorn api.server:app --host 0.0.0.0 --port 8000 --workers 4 --limit-concurrency 100

Audit fixes applied
-------------------
  CVSS 6.5  Rate limiting    -> slowapi added globally
  CORS       Tightened        -> explicit origin, no wildcard
  /docs      Disabled in prod -> controlled by ENABLE_DOCS env var
"""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from api.routes.ingest  import router as ingest_router, limiter
from api.routes.metrics import router as metrics_router

VERSION     = open("VERSION").read().strip() if os.path.exists("VERSION") else "1.0.0"
ENABLE_DOCS = os.getenv("ENABLE_DOCS", "true").lower() == "true"
CORS_ORIGIN = os.getenv("CORS_ORIGIN", "https://safe.teosegypt.com")


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title="Safe Ingestion Engine",
    description="PII-scrubbing URL ingestion API. Auth: X-API-Key: sk-safe-XXXXXXXXXX",
    version=VERSION,
    docs_url="/docs"   if ENABLE_DOCS else None,
    redoc_url="/redoc" if ENABLE_DOCS else None,
    lifespan=lifespan,
)

# ── Rate limiting (global) ────────────────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# ── CORS — explicit origin, never wildcard ────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[CORS_ORIGIN],
    allow_methods=["GET", "POST"],
    allow_headers=["X-API-Key", "Content-Type"],
)

# ── Security headers ──────────────────────────────────────────────────────────
@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"]  = "nosniff"
    response.headers["X-Frame-Options"]         = "DENY"
    response.headers["Referrer-Policy"]         = "no-referrer"
    response.headers["X-XSS-Protection"]        = "0"
    return response

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(ingest_router)
app.include_router(metrics_router)


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok", "version": VERSION}
