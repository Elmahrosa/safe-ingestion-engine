from __future__ import annotations

import secrets
import uuid

import redis
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, HttpUrl
from sqlalchemy import select

from api.dependencies import require_api_key
from api.routes.metrics import REQUEST_COUNT, REQUEST_DURATION
from core.auth import deduct_credit, get_key_info, hash_api_key, register_api_key
from core.config import get_settings
from core.database import session_scope
from core.models import Job
from infrastructure.queue.tasks import ingest_url_task
from security.rate_limit import limiter

router = APIRouter()
settings = get_settings()
redis_client = redis.Redis.from_url(settings.redis_url, decode_responses=True)

PLAN_CREDITS = {
    "trial": 5,
    "starter": 100,
    "growth": 1000,
    "enterprise": 50000,
}


class IngestRequest(BaseModel):
    url: HttpUrl
    idempotency_key: str | None = None


class RegisterKeyPayload(BaseModel):
    api_key: str
    plan: str = "starter"
    credits: int | None = None
    tx_hash: str | None = None


@router.post("/v1/ingest_async")
@limiter.limit("10/minute")
async def enqueue_ingest(
    request: Request,
    payload: IngestRequest,
    api_key: str = Depends(require_api_key),
):
    with REQUEST_DURATION.time():
        try:
            if payload.idempotency_key:
                cache_key = f"idempotent:{payload.idempotency_key}"
                existing = redis_client.get(cache_key)
                if existing:
                    REQUEST_COUNT.labels(status="duplicate").inc()
                    return {"job_id": existing, "status": "duplicate"}

            if not deduct_credit(api_key):
                REQUEST_COUNT.labels(status="no_credits").inc()
                raise HTTPException(
                    status_code=402,
                    detail="insufficient credits — top up before submitting another job",
                )

            job_id = str(uuid.uuid4())
            with session_scope() as session:
                session.add(
                    Job(
                        job_id=job_id,
                        source_url=str(payload.url),
                        status="queued",
                        api_key_hash=hash_api_key(api_key),
                    )
                )

            ingest_url_task.delay(job_id=job_id)

            if payload.idempotency_key:
                redis_client.setex(cache_key, 86400, job_id)

            REQUEST_COUNT.labels(status="queued").inc()
            return {"job_id": job_id, "status": "queued"}
        except HTTPException:
            raise
        except Exception as exc:
            REQUEST_COUNT.labels(status="error").inc()
            raise HTTPException(status_code=500, detail=f"failed to enqueue job: {exc}") from exc


@router.get("/v1/jobs/{job_id}")
async def get_job(job_id: str, api_key: str = Depends(require_api_key)):
    key_hash = hash_api_key(api_key)
    with session_scope() as session:
        job = session.scalar(
            select(Job).where(
                Job.job_id == job_id,
                Job.api_key_hash == key_hash,
            )
        )
        if job is None:
            raise HTTPException(status_code=404, detail="job not found")

        return {
            "job_id": job.job_id,
            "status": job.status,
            "source_url": job.source_url,
            "pii_found": job.pii_found,
            "result_excerpt": job.result_excerpt,
            "error_message": job.error_message,
            "created_at": job.created_at.isoformat(),
            "updated_at": job.updated_at.isoformat(),
        }


@router.get("/v1/account")
async def get_account(api_key: str = Depends(require_api_key)):
    info = get_key_info(api_key)
    if not info["valid"]:
        raise HTTPException(status_code=401, detail="invalid api key")
    return info


@router.post("/internal/register-key")
async def register_key(request: Request, payload: RegisterKeyPayload):
    incoming_secret = request.headers.get("x-webhook-secret", "")
    if not settings.gas_webhook_secret:
        raise HTTPException(status_code=500, detail="webhook secret not configured on server")
    if not secrets.compare_digest(incoming_secret, settings.gas_webhook_secret):
        raise HTTPException(status_code=403, detail="forbidden")

    plan = payload.plan.lower()
    if plan not in PLAN_CREDITS:
        raise HTTPException(
            status_code=400,
            detail=f"unknown plan '{plan}'. valid: {sorted(PLAN_CREDITS)}",
        )

    credits = payload.credits if payload.credits is not None else PLAN_CREDITS[plan]
    key_hash = register_api_key(payload.api_key, credits=credits, plan=plan)

    return {
        "registered": True,
        "hash_preview": key_hash[:12],
        "plan": plan,
        "credits": credits,
        "tx_hash": payload.tx_hash,
    }
