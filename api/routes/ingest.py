"""
api/routes/ingest.py
====================
POST /v1/ingest        — submit a URL for async ingestion
GET  /v1/jobs/{job_id} — poll job status (key-scoped, no enum)
POST /internal/register-key — GAS billing bridge (hidden from docs)

Audit fixes applied
-------------------
  CVSS 8.2  SSRF          -> ssrf_safe_url() on every URL before queuing
  CVSS 7.5  Job enum      -> UUIDv4 job IDs + assert_job_owner() on GET
  CVSS 6.5  Rate limits   -> slowapi @limiter.limit on ingest + register-key
  Timing    Secret check  -> hmac.compare_digest (constant-time)
"""

import hmac
import os
import uuid
from datetime import datetime, timezone
from typing import Optional

import redis
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, HttpUrl
from slowapi import Limiter
from slowapi.util import get_remote_address

from core.auth import require_api_key, register_key
from core.security import ssrf_safe_url, assert_job_owner, RATE_INGEST, RATE_AUTH

router  = APIRouter()
limiter = Limiter(key_func=get_remote_address)

REDIS_URL          = os.getenv("REDIS_URL", "redis://localhost:6379/0")
GAS_WEBHOOK_SECRET = os.getenv("GAS_WEBHOOK_SECRET", "")

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
    status: str
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
@limiter.limit(RATE_INGEST)
async def submit_ingest(
    request: Request,
    body: IngestRequest,
    api_key: str = Depends(require_api_key),
):
    """Submit a single URL for async PII-scrubbed ingestion."""
    # SSRF guard — rejects private IPs, IPv6 loopback, decimal IPs, xip.io tricks
    ssrf_safe_url(str(body.url))

    job_id = str(uuid.uuid4())   # UUIDv4 — not guessable/sequential
    now    = datetime.now(timezone.utc).isoformat()

    _r.hset(f"job:{job_id}", mapping={
        "status":     "queued",
        "url":        str(body.url),
        "scrub_pii":  str(body.scrub_pii),
        "api_key":    api_key,
        "created_at": now,
        "updated_at": now,
    })
    _r.expire(f"job:{job_id}", 86400)

    # TODO: push to Celery — JSON serializer only (no pickle)
    # from workers.tasks import ingest_url
    # ingest_url.apply_async(args=[job_id, str(body.url), body.scrub_pii],
    #                        serializer="json")

    return IngestResponse(job_id=job_id, status="queued", submitted_at=now)


@router.get("/v1/jobs/{job_id}", response_model=JobStatus, tags=["Ingestion"])
@limiter.limit("120/minute")
async def get_job_status(
    request: Request,
    job_id: str,
    api_key: str = Depends(require_api_key),
):
    """
    Poll job status. Returns 404 for non-existent OR cross-key jobs.
    Never 403 — avoids confirming whether a job exists to the wrong key.
    """
    data = _r.hgetall(f"job:{job_id}")
    if not data:
        raise HTTPException(status_code=404, detail="Job not found or expired.")

    assert_job_owner(data, api_key)

    return JobStatus(
        job_id=job_id,
        status=data.get("status", "unknown"),
        result=None,
        error=data.get("error"),
        created_at=data.get("created_at"),
        updated_at=data.get("updated_at"),
    )


@router.post("/internal/register-key", tags=["Internal"], include_in_schema=False)
@limiter.limit(RATE_AUTH)
async def register_api_key(request: Request, body: RegisterKeyRequest):
    """
    GAS billing bridge. Rate-limited + constant-time secret compare.
    NOT exposed in /docs.
    """
    if not GAS_WEBHOOK_SECRET:
        raise HTTPException(status_code=503, detail="Webhook secret not configured.")

    if not hmac.compare_digest(body.secret, GAS_WEBHOOK_SECRET):
        raise HTTPException(status_code=403, detail="Invalid webhook secret.")

    register_key(body.api_key, ttl=body.ttl_days * 86400)
    return {"ok": True, "message": "Key registered."}
