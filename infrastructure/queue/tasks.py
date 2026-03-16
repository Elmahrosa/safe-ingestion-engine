from __future__ import annotations

import asyncio
import hashlib

import redis
from celery.utils.log import get_task_logger
from sqlalchemy import select

from collectors.http_connector import HTTPConnector
from core.config import get_settings
from core.database import session_scope
from core.logging import configure_logging
from core.models import Job, JobStatus, transition
from core.policy import PolicyEngine
from core.pii import scrub_text
from infrastructure.queue.celery_app import celery_app
from services.ingestion_service import IngestionService

settings = get_settings()
configure_logging(settings.log_level)
log = get_task_logger(__name__)

MAX_EXCERPT_CHARS = 2000


def _hash_content(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


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
        job.status = transition(job.status, JobStatus.RUNNING)
        job.attempt_count += 1
        from datetime import datetime, timezone
        job.last_attempt = datetime.now(timezone.utc)
        url = job.source_url
        domain = job.domain or ""

    try:
        # Policy check
        allowed, reason = policy_engine.evaluate(url)
        if not allowed:
            with session_scope() as session:
                db_job = session.scalar(select(Job).where(Job.job_id == job_id))
                if db_job:
                    db_job.status = transition(db_job.status, JobStatus.BLOCKED)
                    db_job.error_message = reason
                    db_job.security_event = True
            log.warning("job blocked", extra={"job_id": job_id, "reason": reason})
            return {"job_id": job_id, "status": "BLOCKED", "reason": reason}

        # Fetch
        result = asyncio.run(connector.fetch(url))
        raw_content = result.content

        # PII scrub
        pii_result = scrub_text(raw_content)
        clean_content = pii_result.text
        pii_count = pii_result.count

        # Content hash
        content_hash = _hash_content(clean_content)

        # Release domain concurrency slot
        policy_engine.concurrency.release(domain)

        with session_scope() as session:
            db_job = session.scalar(select(Job).where(Job.job_id == job_id))
            if db_job is None:
                raise ValueError(f"job vanished: {job_id}")
            db_job.status = transition(db_job.status, JobStatus.COMPLETED)
            db_job.result_excerpt = clean_content[:MAX_EXCERPT_CHARS]
            db_job.content_hash = content_hash
            db_job.pii_found = pii_count
            from datetime import datetime, timezone
            db_job.completed_at = datetime.now(timezone.utc)

        log.info("job completed", extra={
            "job_id": job_id, "url": url,
            "pii_count": pii_count, "content_hash": content_hash[:12]
        })
        return {"job_id": job_id, "status": "COMPLETED",
                "content_hash": content_hash, "pii_found": pii_count}

    except Exception as exc:
        policy_engine.concurrency.release(domain)
        is_retry = self.request.retries < self.max_retries

        with session_scope() as session:
            db_job = session.scalar(select(Job).where(Job.job_id == job_id))
            if db_job is not None:
                next_status = JobStatus.RETRYING if is_retry else JobStatus.FAILED
                try:
                    db_job.status = transition(db_job.status, next_status)
                except ValueError:
                    db_job.status = JobStatus.FAILED
                db_job.error_message = str(exc)
                db_job.security_event = True

        log.exception("job failed", extra={"job_id": job_id, "url": url})
        raise