from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, HttpUrl

from api.dependencies import require_api_key
from core.config import get_settings
from infrastructure.queue.tasks import ingest_url_task
from security.rate_limit import limiter

router = APIRouter()
settings = get_settings()

class IngestRequest(BaseModel):
    url: HttpUrl

@router.post("/ingest")
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def enqueue_ingest(request: Request, payload: IngestRequest, api_key: str = Depends(require_api_key)):
    try:
        task = ingest_url_task.delay(str(payload.url), api_key)
        return {"job_id": task.id, "status": "queued"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"failed to enqueue job: {exc}")
