import os
import time
from urllib.parse import urlparse

from api.celery_app import celery_app

from core.database import init_db, log_audit, log_metric, insert_raw
from core.policy import PolicyEngine
from core.compliance import ComplianceGuard
from collectors.scraper import SafeScraper
from core.pii import PIIScrubber

# Optional AI PII detection (report only)
try:
    from core.pii_ai import detect_pii_ai
except Exception:
    detect_pii_ai = None


policy_engine = PolicyEngine("policies/policy.yml")


def get_user_agent():
    return os.getenv(
        "USER_AGENT",
        "SafeIngestionBot/1.0 (+contact@example.org)"
    )


@celery_app.task(bind=True)
def ingest_job(self, url: str, user_name: str, allowlist_patterns: list[str], pii_mode: str = "redact"):
    """
    Background ingestion task.

    Enforces:
    - Domain policy rules
    - Allowlist scope
    - robots.txt compliance
    - audit logging
    """

    conn = init_db()

    # -------------------------
    # 1 Policy Engine
    # -------------------------
    policy = policy_engine.decide(url)

    if not policy.allowed:
        log_audit(conn, url, policy.status, policy.reason)
        log_metric(conn, url, policy.status, 0, 0, None)

        return {
            "status": policy.status,
            "reason": policy.reason
        }

    # -------------------------
    # 2 Compliance Guard
    # -------------------------
    guard = ComplianceGuard(allowlist_patterns=allowlist_patterns)

    allowed, status, reason = guard.is_permitted(url)

    if not allowed:
        log_audit(conn, url, status, reason)
        log_metric(conn, url, status, 0, 0, None)

        return {
            "status": status,
            "reason": reason
        }

    # -------------------------
    # 3 Fetch page
    # -------------------------
    scraper = SafeScraper(
        guard,
        user_agent=get_user_agent()
    )

    start = time.time()

    try:
        html, content_type, size_bytes = scraper.fetch(url)
        elapsed_ms = int((time.time() - start) * 1000)

    except Exception as e:

        elapsed_ms = int((time.time() - start) * 1000)

        log_audit(conn, url, "FETCH_ERROR", str(e))
        log_metric(conn, url, "FETCH_ERROR", elapsed_ms, 0, None)

        return {
            "status": "FETCH_ERROR",
            "error": str(e)
        }

    # -------------------------
    # 4 Regex PII scrub
    # -------------------------
    scrubber = PIIScrubber(
        mode=pii_mode,
        salt=os.getenv("PII_SALT", "")
    )

    scrubbed = scrubber.scrub(html)

    # -------------------------
    # 5 AI PII detection (report only)
    # -------------------------
    ai_entities = []

    if detect_pii_ai:
        try:
            ai_result = detect_pii_ai(html)
            if ai_result.available:
                ai_entities = ai_result.entities
        except Exception:
            pass

    # -------------------------
    # 6 Store cleaned data
    # -------------------------
    insert_raw(
        conn,
        source_url=url,
        content=scrubbed.text,
        pii_counts=scrubbed.counts,
        content_type=content_type
    )

    # -------------------------
    # 7 Audit + Metrics
    # -------------------------
    log_audit(
        conn,
        url,
        "SUCCESS",
        f"bytes={size_bytes} regex_pii={scrubbed.counts} ai_entities={len(ai_entities)}"
    )

    log_metric(
        conn,
        url,
        "SUCCESS",
        elapsed_ms,
        size_bytes,
        content_type
    )

    return {
        "status": "SUCCESS",
        "url": url,
        "content_type": content_type,
        "size_bytes": size_bytes,
        "latency_ms": elapsed_ms,
        "pii_regex_counts": scrubbed.counts,
        "pii_ai_entities": ai_entities
    }
