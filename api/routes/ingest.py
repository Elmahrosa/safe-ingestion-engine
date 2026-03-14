from __future__ import annotations

import uuid

import redis
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, HttpUrl

from api.dependencies import require_api_key
from api.routes.metrics import REQUEST_COUNT, REQUEST_DURATION
from core.auth import hash_api_key
from core.config import get_settings
from core.database import session_scope
from core.models import Job
from infrastructure.queue.tasks import ingest_url_task
from security.rate_limit import limiter


router = APIRouter()
settings = get_settings()
redis_client = redis.Redis.from_url(settings.redis_url, decode_responses=True)


class IngestRequest(BaseModel):
    url: HttpUrl
    idempotency_key: str | None = None


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
        except Exception as exc:
            REQUEST_COUNT.labels(status="error").inc()
            raise HTTPException(status_code=500, detail=f"failed to enqueue job: {exc}") from exc
