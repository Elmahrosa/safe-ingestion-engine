# First, add this import at the TOP of the file if not already present:
from collectors.http_connector import SSRFBlockedError

# Then replace the broad exception handler in ingest_url_task() with this:

except Exception as exc:
    policy_engine.concurrency.release(domain)
    is_retry = self.request.retries < self.max_retries
    
    # ✅ Only mark as security_event for SSRF blocks
    is_security_event = isinstance(exc, SSRFBlockedError)
    
    with session_scope() as session:
        db_job = session.scalar(select(Job).where(Job.job_id == job_id))
        if db_job is not None:
            next_status = JobStatus.RETRYING if is_retry else JobStatus.FAILED
            try:
                db_job.status = transition(db_job.status, next_status)
            except ValueError:
                db_job.status = JobStatus.FAILED
            db_job.error_message = str(exc)
            db_job.security_event = is_security_event  # ✅ Narrowed scope
    log.exception("job failed", extra={
        "job_id": job_id, 
        "url": url,
        "security_event": is_security_event,  # ✅ Explicit in logs too
    })
    raise
