from __future__ import annotations

import hashlib
import secrets
import uuid
from urllib.parse import urlparse

import redis
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, HttpUrl
from sqlalchemy import select

from api.dependencies import require_api_key
from api.routes.metrics import REQUEST_COUNT, REQUEST_DURATION
from core.auth import deduct_credit, get_key_info, hash_api_key, register_api_key
from core.config import get_settings
from core.database import session_scope
from core.models import Job, JobStatus
from infrastructure.queue.tasks import ingest_url_task
from security.rate_limit import limiter

router = APIRouter()
settings = get_settings()
redis_client = redis.Redis.from_url(settings.redis_url, decode_responses=True)

PLAN_CREDITS = {
    "trial":      5,
    "starter":    100,
    "growth":     1000,
    "enterprise": 50000,
}


class IngestRequest(BaseModel):
    url: HttpUrl
    idempotency_key: str | None = None
    tenant_id: str | None = None


class RegisterKeyPayload(BaseModel):
    api_key: str
    plan: str = "starter"
    credits: int | None = None
    tx_hash: str | None = None


def _extract_domain(url: str) -> str:
    try:
        return urlparse(url).netloc or "unknown"
    except Exception:
        return "unknown"


def _hash_content(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


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
                    detail="insufficient credits",
                )

            job_id = str(uuid.uuid4())
            domain = _extract_domain(str(payload.url))

            with session_scope() as session:
                session.add(Job(
                    job_id=job_id,
                    source_url=str(payload.url),
                    domain=domain,
                    tenant_id=payload.tenant_id,
                    status=JobStatus.PENDING,
                    api_key_hash=hash_api_key(api_key),
                ))

            ingest_url_task.delay(job_id=job_id)

            if payload.idempotency_key:
                redis_client.setex(
                    f"idempotent:{payload.idempotency_key}", 86400, job_id
                )

            REQUEST_COUNT.labels(status="queued").inc()
            return {"job_id": job_id, "status": JobStatus.PENDING.value}

        except HTTPException:
            raise
        except Exception as exc:
            REQUEST_COUNT.labels(status="error").inc()
            raise HTTPException(
                status_code=500, detail=f"failed to enqueue job: {exc}"
            ) from exc


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
            "status": job.status.value,
            "domain": job.domain,
            "tenant_id": job.tenant_id,
            "source_url": job.source_url,
            "pii_found": job.pii_found,
            "content_hash": job.content_hash,
            "attempt_count": job.attempt_count,
            "result_excerpt": job.result_excerpt,
            "error_message": job.error_message,
            "created_at": job.created_at.isoformat(),
            "updated_at": job.updated_at.isoformat(),
            "completed_at": (
                job.completed_at.isoformat() if job.completed_at else None
            ),
        }


@router.get("/v1/jobs")
async def list_jobs(
    api_key: str = Depends(require_api_key),
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
):
    key_hash = hash_api_key(api_key)
    with session_scope() as session:
        q = select(Job).where(Job.api_key_hash == key_hash)
        if status:
            try:
                q = q.where(Job.status == JobStatus(status.upper()))
            except ValueError:
                raise HTTPException(
                    status_code=400, detail=f"invalid status: {status}"
                )
        q = (
            q.order_by(Job.created_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
        jobs = session.scalars(q).all()
        return {
            "page": page,
            "per_page": per_page,
            "jobs": [
                {
                    "job_id": j.job_id,
                    "status": j.status.value,
                    "domain": j.domain,
                    "source_url": j.source_url,
                    "pii_found": j.pii_found,
                    "content_hash": j.content_hash,
                    "created_at": j.created_at.isoformat(),
                }
                for j in jobs
            ],
        }


@router.get("/v1/audit")
async def get_audit(
    api_key: str = Depends(require_api_key),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
):
    key_hash = hash_api_key(api_key)
    with session_scope() as session:
        q = (
            select(Job)
            .where(Job.api_key_hash == key_hash)
            .order_by(Job.created_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
        jobs = session.scalars(q).all()
        return {
            "page": page,
            "per_page": per_page,
            "events": [
                {
                    "job_id": j.job_id,
                    "status": j.status.value,
                    "domain": j.domain,
                    "source_url": j.source_url,
                    "pii_found": j.pii_found,
                    "content_hash": j.content_hash,
                    "security_event": j.security_event,
                    "error_message": j.error_message,
                    "attempt_count": j.attempt_count,
                    "created_at": j.created_at.isoformat(),
                    "completed_at": (
                        j.completed_at.isoformat() if j.completed_at else None
                    ),
                }
                for j in jobs
            ],
        }


@router.get("/v1/domains")
async def get_domains(api_key: str = Depends(require_api_key)):
    key_hash = hash_api_key(api_key)
    with session_scope() as session:
        jobs = session.scalars(
            select(Job).where(Job.api_key_hash == key_hash)
        ).all()
        domain_stats: dict[str, dict] = {}
        for j in jobs:
            d = j.domain or "unknown"
            if d not in domain_stats:
                domain_stats[d] = {
                    "domain": d,
                    "total": 0,
                    "completed": 0,
                    "blocked": 0,
                    "failed": 0,
                    "last_crawled": None,
                }
            domain_stats[d]["total"] += 1
            if j.status == JobStatus.COMPLETED:
                domain_stats[d]["completed"] += 1
            elif j.status == JobStatus.BLOCKED:
                domain_stats[d]["blocked"] += 1
            elif j.status == JobStatus.FAILED:
                domain_stats[d]["failed"] += 1
            ts = j.updated_at.isoformat()
            if (
                not domain_stats[d]["last_crawled"]
                or ts > domain_stats[d]["last_crawled"]
            ):
                domain_stats[d]["last_crawled"] = ts
        return {"domains": list(domain_stats.values())}


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
        raise HTTPException(
            status_code=500, detail="webhook secret not configured"
        )
    if not secrets.compare_digest(incoming_secret, settings.gas_webhook_secret):
        raise HTTPException(status_code=403, detail="forbidden")
    plan = payload.plan.lower()
    if plan not in PLAN_CREDITS:
        raise HTTPException(
            status_code=400,
            detail=f"unknown plan. valid: {sorted(PLAN_CREDITS)}",
        )
    credits = (
        payload.credits if payload.credits is not None else PLAN_CREDITS[plan]
    )
    key_hash = register_api_key(payload.api_key, credits=credits, plan=plan)
    return {
        "registered": True,
        "hash_preview": key_hash[:12],
        "plan": plan,
        "credits": credits,
        "tx_hash": payload.tx_hash,
    }