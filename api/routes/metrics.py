"""
api/routes/metrics.py
=====================
GET /metrics — Prometheus-compatible plaintext metrics
GET /v1/status — JSON health + counters for dashboards
"""

import os
import time
from datetime import datetime, timezone

import redis
from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

router = APIRouter()

REDIS_URL  = os.getenv("REDIS_URL", "redis://localhost:6379/0")
START_TIME = time.time()

try:
    _r = redis.from_url(REDIS_URL, decode_responses=True)
except Exception:
    _r = None


def _redis_ok() -> bool:
    try:
        return _r is not None and _r.ping()
    except Exception:
        return False


def _count_jobs(status: str) -> int:
    try:
        keys = _r.keys(f"job:*") if _r else []
        count = 0
        for k in keys:
            if _r.hget(k, "status") == status:
                count += 1
        return count
    except Exception:
        return -1


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/metrics", response_class=PlainTextResponse, tags=["Observability"])
async def prometheus_metrics():
    """Prometheus-compatible plaintext metrics endpoint."""
    uptime   = time.time() - START_TIME
    redis_up = 1 if _redis_ok() else 0
    queued   = _count_jobs("queued")
    done     = _count_jobs("done")
    failed   = _count_jobs("failed")

    lines = [
        "# HELP safe_uptime_seconds Time since API server started",
        "# TYPE safe_uptime_seconds gauge",
        f"safe_uptime_seconds {uptime:.2f}",
        "",
        "# HELP safe_redis_up Redis connectivity (1=up, 0=down)",
        "# TYPE safe_redis_up gauge",
        f"safe_redis_up {redis_up}",
        "",
        "# HELP safe_jobs_queued Jobs currently queued",
        "# TYPE safe_jobs_queued gauge",
        f"safe_jobs_queued {queued}",
        "",
        "# HELP safe_jobs_done Jobs completed successfully",
        "# TYPE safe_jobs_done gauge",
        f"safe_jobs_done {done}",
        "",
        "# HELP safe_jobs_failed Jobs that failed",
        "# TYPE safe_jobs_failed gauge",
        f"safe_jobs_failed {failed}",
    ]
    return "\n".join(lines)


@router.get("/v1/status", tags=["Observability"])
async def api_status():
    """JSON status — for dashboards and uptime monitors."""
    return {
        "ok":         True,
        "version":    open("VERSION").read().strip() if os.path.exists("VERSION") else "unknown",
        "uptime_sec": round(time.time() - START_TIME, 1),
        "redis":      "up" if _redis_ok() else "down",
        "timestamp":  datetime.now(timezone.utc).isoformat(),
    }
