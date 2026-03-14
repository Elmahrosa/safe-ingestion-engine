from __future__ import annotations

import asyncio

import redis
from celery.utils.log import get_task_logger
from sqlalchemy import select

from collectors.http_connector import HTTPConnector
from core.database import session_scope
from core.config import get_settings
from core.logging import configure_logging
from core.models import Job
from core.policy import PolicyEngine
from infrastructure.queue.celery_app import celery_app
from services.ingestion_service import IngestionService


settings = get_settings()
configure_logging(settings.log_level)
log = get_task_logger(__name__)


@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=60,
    retry_jitter=True,
    max_retries=3,
)
def ingest_url_task(self, job_id: str):
    redis_client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
    connector = HTTPConnector()
    policy_engine = PolicyEngine(redis_client)
    service = IngestionService(connector, policy_engine)

    with session_scope() as session:
        job = session.scalar(select(Job).where(Job.job_id == job_id))
        if job is None:
            raise ValueError(f"job not found: {job_id}")
        job.status = "running"
        url = job.source_url

    try:
        cleaned, pii_count = asyncio.run(service.ingest(url))
        with session_scope() as session:
            db_job = session.scalar(select(Job).where(Job.job_id == job_id))
            if db_job is None:
                raise ValueError(f"job vanished: {job_id}")
            db_job.status = "completed"
            db_job.result_excerpt = cleaned[:2000]
            db_job.pii_found = pii_count
        log.info("job completed", extra={"job_id": job_id, "url": url})
        return {"job_id": job_id, "status": "completed"}
    except Exception as exc:
        with session_scope() as session:
            db_job = session.scalar(select(Job).where(Job.job_id == job_id))
            if db_job is not None:
                db_job.status = "failed"
                db_job.error_message = str(exc)
                db_job.security_event = True
        log.exception("job failed", extra={"job_id": job_id, "url": url})
        raise
