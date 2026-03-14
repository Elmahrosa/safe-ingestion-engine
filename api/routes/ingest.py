"""
api/routes/ingest.py
====================
POST /v1/ingest        — submit a URL for async ingestion
GET  /v1/jobs/{job_id} — poll job status
POST /internal/register-key — GAS billing bridge (webhook)
"""

import hashlib
import os
import uuid
from datetime import datetime, timezone
from typing import Optional

import redis
from fastapi import APIRouter, Depends, HTTPException, Header, status
from pydantic import BaseModel, HttpUrl

from core.auth import require_api_key, register_key

router = APIRouter()

REDIS_URL           = os.getenv("REDIS_URL", "redis://localhost:6379/0")
GAS_WEBHOOK_SECRET  = os.getenv("GAS_WEBHOOK_SECRET", "")
MAX_URLS            = int(os.getenv("MAX_INGEST_URLS_PER_REQUEST", "10"))

_r = redis.from_url(REDIS_URL, decode_responses=True)


# ── Schemas ───────────────────────────────────────────────────────────────────

class IngestRequest(BaseModel):
    url: HttpUrl
    scrub_pii: bool = True
    webhook_url: Optional[str] = None


class IngestResponse(BaseModel):
    job_id: str
    status: str
    submitted_at: str


class JobStatus(BaseModel):
    job_id: str
    status: str          # queued | processing | done | failed
    result: Optional[dict] = None
    error: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class RegisterKeyRequest(BaseModel):
    api_key: str
    secret: str
    ttl_days: int = 31


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/v1/ingest", response_model=IngestResponse, tags=["Ingestion"])
async def submit_ingest(
    body: IngestRequest,
    api_key: str = Depends(require_api_key),
):
    """Submit a single URL for async PII-scrubbed ingestion."""
    job_id = str(uuid.uuid4())
    now    = datetime.now(timezone.utc).isoformat()

    # Store job metadata in Redis (TTL 24 h)
    _r.hset(f"job:{job_id}", mapping={
        "status":     "queued",
        "url":        str(body.url),
        "scrub_pii":  str(body.scrub_pii),
        "api_key":    api_key,
        "created_at": now,
        "updated_at": now,
    })
    _r.expire(f"job:{job_id}", 86400)

    # TODO: push to Celery — currently stubbed
    # from workers.tasks import ingest_url
    # ingest_url.delay(job_id, str(body.url), body.scrub_pii)

    return IngestResponse(job_id=job_id, status="queued", submitted_at=now)


@router.get("/v1/jobs/{job_id}", response_model=JobStatus, tags=["Ingestion"])
async def get_job_status(
    job_id: str,
    api_key: str = Depends(require_api_key),
):
    """Poll the status of a previously submitted ingestion job."""
    data = _r.hgetall(f"job:{job_id}")
    if not data:
        raise HTTPException(status_code=404, detail="Job not found or expired.")
    return JobStatus(
        job_id=job_id,
        status=data.get("status", "unknown"),
        result=None,          # populated by worker when done
        error=data.get("error"),
        created_at=data.get("created_at"),
        updated_at=data.get("updated_at"),
    )


@router.post("/internal/register-key", tags=["Internal"], include_in_schema=False)
async def register_api_key(body: RegisterKeyRequest):
    """
    GAS billing bridge — called by Google Apps Script after payment confirmation.
    Requires GAS_WEBHOOK_SECRET header match.
    NOT included in public /docs.
    """
    if not GAS_WEBHOOK_SECRET:
        raise HTTPException(status_code=503, detail="Webhook secret not configured.")
    if body.secret != GAS_WEBHOOK_SECRET:
        raise HTTPException(status_code=403, detail="Invalid webhook secret.")

    ttl = body.ttl_days * 86400
    register_key(body.api_key, ttl=ttl)
    return {"ok": True, "message": "Key registered."}
