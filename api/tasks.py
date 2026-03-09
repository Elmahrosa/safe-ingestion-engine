"""
api/tasks.py — Celery background tasks.
Fixes:
  - DB connection leak (try/finally)
  - Correct imports of log_audit/log_metrics/insert_raw
  - Sheet deduct called on job completion (api_key param added)
"""
import os, sqlite3, time
from datetime import datetime
import httpx
from celery import Celery
from collectors.scraper import SafeScraper
from core.database import get_db_path, log_audit, log_metrics, insert_raw
from core.pii import PIIScrubber
from core.policy import PolicyEngine

REDIS_URL         = os.getenv("REDIS_URL", "redis://redis:6379/0")
USER_AGENT        = os.getenv("USER_AGENT", "SafeSaaS/1.0")
SHEET_WEBHOOK_URL = os.getenv("SHEET_WEBHOOK_URL", "")
SHEET_API_SECRET  = os.getenv("SHEET_API_SECRET", "")

celery_app = Celery("safe_ingestion", broker=REDIS_URL, backend=REDIS_URL)
celery_app.conf.update(task_serializer="json", result_serializer="json",
    accept_content=["json"], timezone="UTC", enable_utc=True, task_track_started=True)

def _update_job(conn, job_id, **fields):
    set_clause = ", ".join(f"{k}=?" for k in fields)
    conn.execute(f"UPDATE jobs SET {set_clause} WHERE job_id=?", list(fields.values())+[job_id])
    conn.commit()

def _sheet_deduct(api_key, amount=1):
    if not SHEET_WEBHOOK_URL or not SHEET_API_SECRET or not api_key:
        return True
    try:
        r = httpx.get(SHEET_WEBHOOK_URL,
            params={"action":"deduct","api_key":api_key,"amount":amount,"secret":SHEET_API_SECRET}, timeout=5.0)
        return r.json().get("ok", False)
    except:
        return False

@celery_app.task(bind=True, name="ingest_url")
def ingest_url_task(self, job_id, url, user_id, scrub_pii=True, scrub_pii_mode="redact",
                    respect_robots=True, timeout=30, tier="basic", api_key=""):
    conn = sqlite3.connect(get_db_path())
    try:
        _update_job(conn, job_id, status="processing", updated_at=datetime.utcnow().isoformat())

        policy = PolicyEngine()
        decision = policy.evaluate(url)
        if not decision.get("allowed", True):
            _update_job(conn, job_id, status="blocked", error_msg=decision.get("reason","Blocked by policy"), updated_at=datetime.utcnow().isoformat())
            log_audit(conn, job_id=job_id, user_id=user_id, url=url, status="blocked", tier=tier, reason=decision.get("reason"))
            return

        scraper = SafeScraper(user_agent=USER_AGENT)
        fetch_result = scraper.fetch_with_metrics(url, timeout=timeout)
        if not fetch_result.get("success"):
            _update_job(conn, job_id, status="failed", error_msg=fetch_result.get("error","Fetch failed"), updated_at=datetime.utcnow().isoformat())
            log_audit(conn, job_id=job_id, user_id=user_id, url=url, status="failed", tier=tier, reason=fetch_result.get("error"))
            return

        raw_content   = fetch_result["content"]
        bytes_fetched = fetch_result["bytes"]
        latency_ms    = fetch_result["latency_ms"]

        pii_removed = 0
        content = raw_content
        if scrub_pii:
            scrubber = PIIScrubber(mode=scrub_pii_mode)
            content, pii_removed = scrubber.scrub(raw_content)

        insert_raw(conn, job_id=job_id, user_id=user_id, url=url, content=raw_content)
        _update_job(conn, job_id, status="completed", result_content=content,
            bytes_fetched=bytes_fetched, pii_removed=pii_removed, latency_ms=latency_ms,
            scrub_mode=scrub_pii_mode if scrub_pii else "none", tier=tier, updated_at=datetime.utcnow().isoformat())

        log_audit(conn, job_id=job_id, user_id=user_id, url=url, status="completed",
            tier=tier, latency_ms=latency_ms, bytes_fetched=bytes_fetched, pii_removed=pii_removed)
        log_metrics(conn, job_id=job_id, user_id=user_id, latency_ms=latency_ms,
            bytes_fetched=bytes_fetched, pii_removed=pii_removed, tier=tier, status="completed")

        # Deduct credit in Sheet only on success
        _sheet_deduct(api_key, amount=1)

    except Exception as exc:
        try:
            _update_job(conn, job_id, status="failed", error_msg=str(exc), updated_at=datetime.utcnow().isoformat())
            log_audit(conn, job_id=job_id, user_id=user_id, url=url, status="failed", tier=tier, reason=str(exc))
        except:
            pass
        raise self.retry(exc=exc, countdown=5, max_retries=2)
    finally:
        conn.close()
