# fix_03_metrics_auth.py
# ─────────────────────────────────────────────────────────────────────────────
# FINDING (HIGH): GET /metrics is unauthenticated and publicly reachable.
# It leaks job counts, domain names, and timing histograms.
#
# FILE: api/routes/metrics.py
# ─────────────────────────────────────────────────────────────────────────────

PATCH = '''
from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

from core.config import get_settings

REQUEST_COUNT = Counter("ingestion_requests_total", "Total ingestion requests", ["status"])
REQUEST_DURATION = Histogram("ingestion_request_duration_seconds", "Request duration")

router = APIRouter()
_security = HTTPBasic()


def _require_metrics_auth(credentials: HTTPBasicCredentials = Depends(_security)) -> None:
    """
    Protect /metrics with HTTP Basic Auth.
    Username: metrics
    Password: DASHBOARD_ADMIN_PASSWORD (reuses the existing secret)
    """
    settings = get_settings()
    correct_user = b"metrics"
    correct_pass = settings.dashboard_admin_password.encode()

    ok = (
        secrets.compare_digest(credentials.username.encode(), correct_user)
        and secrets.compare_digest(credentials.password.encode(), correct_pass)
    )
    if not ok:
        raise HTTPException(
            status_code=401,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Basic"},
        )


@router.get("/metrics", dependencies=[Depends(_require_metrics_auth)])
async def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
'''

print("Fix 03: Replace api/routes/metrics.py with PATCH above.")
print("Prometheus scrapers must now supply: metrics:<DASHBOARD_ADMIN_PASSWORD>")
print("Update your Prometheus scrape config accordingly.")
