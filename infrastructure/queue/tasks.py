# fix_07_security_event_flag.py
# ─────────────────────────────────────────────────────────────────────────────
# FINDING (MEDIUM): infrastructure/queue/tasks.py sets security_event=True on
# ALL exceptions — including network timeouts, 404s, DNS failures.
# Only SSRFBlockedError and policy blocks are genuine security events.
# This pollutes the audit log and makes real alerts unactionable.
#
# FILE: infrastructure/queue/tasks.py  — ingest_url_task exception handler
# ─────────────────────────────────────────────────────────────────────────────

# Add this import at the top of tasks.py:
IMPORT_PATCH = "from collectors.http_connector import HTTPConnector, SSRFBlockedError"

# Replace the exception handler block:
EXCEPTION_HANDLER_PATCH = '''
    except Exception as exc:
        policy_engine.concurrency.release(domain)
        is_retry = self.request.retries < self.max_retries

        # Only flag as a security event for genuine security violations.
        # Network timeouts, 404s, and transient errors are NOT security events.
        is_security_event = isinstance(exc, (
            SSRFBlockedError,          # SSRF attempt
            PermissionError,           # policy / robots denial
        ))

        with session_scope() as session:
            db_job = session.scalar(select(Job).where(Job.job_id == job_id))
            if db_job is not None:
                next_status = JobStatus.RETRYING if is_retry else JobStatus.FAILED
                try:
                    db_job.status = transition(db_job.status, next_status)
                except ValueError:
                    db_job.status = JobStatus.FAILED
                db_job.error_message = str(exc)
                db_job.security_event = is_security_event   # ← surgical flag

        log.exception("job failed", extra={
            "job_id": job_id,
            "url": url,
            "security_event": is_security_event,
        })
        raise
'''

print("Fix 07: In infrastructure/queue/tasks.py:")
print("  1. Add SSRFBlockedError to imports")
print("  2. Replace except block with EXCEPTION_HANDLER_PATCH above")
