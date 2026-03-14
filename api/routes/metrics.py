from __future__ import annotations

from fastapi import APIRouter, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest


REQUEST_COUNT = Counter("ingestion_requests_total", "Total ingestion requests", ["status"])
REQUEST_DURATION = Histogram("ingestion_request_duration_seconds", "Request duration")

router = APIRouter()


@router.get("/metrics")
async def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
