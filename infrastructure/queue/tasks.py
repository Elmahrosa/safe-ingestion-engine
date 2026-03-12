import asyncio

import redis
from celery.utils.log import get_task_logger

from collectors.http_connector import HTTPConnector
from core.database import session_scope
from core.models import Job
from core.config import get_settings
from core.policy import PolicyEngine
from infrastructure.queue.celery_app import celery_app
from services.ingestion_service import IngestionService

settings = get_settings()
log = get_task_logger(__name__)

@celery_app.task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_backoff_max=60, retry_jitter=True, max_retries=3)
def ingest_url_task(self, url: str, api_key: str):
    job_id = self.request.id
    redis_client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
    connector = HTTPConnector()
    policy_engine = PolicyEngine(redis_client)
    service = IngestionService(connector, policy_engine)

    with session_scope() as session:
        job = Job(job_id=job_id, source_url=url, status="running")
        session.add(job)

    try:
        cleaned = asyncio.run(service.ingest(url))
        with session_scope() as session:
            db_job = session.query(Job).filter(Job.job_id == job_id).one()
            db_job.status = "completed"
            db_job.result_excerpt = cleaned[:2000]
        log.info("job completed", extra={"job_id": job_id, "url": url})
        return {"job_id": job_id, "status": "completed"}
    except Exception as exc:
        with session_scope() as session:
            db_job = session.query(Job).filter(Job.job_id == job_id).one()
            db_job.status = "failed"
            db_job.error_message = str(exc)
        log.exception("job failed", extra={"job_id": job_id, "url": url})
        raise
