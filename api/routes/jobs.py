from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from api.dependencies import require_api_key
from core.database import session_scope
from core.models import Job

router = APIRouter()


@router.get("/jobs/{job_id}")
async def get_job(job_id: str, api_key: str = Depends(require_api_key)):
    with session_scope() as session:
        job = session.scalar(select(Job).where(Job.job_id == job_id))
        if not job:
            raise HTTPException(status_code=404, detail="job not found")

        return {
            "job_id": job.job_id,
            "status": job.status,
            "source_url": job.source_url,
            "created_at": job.created_at.isoformat(),
            "updated_at": job.updated_at.isoformat(),
            "result_excerpt": (job.result_excerpt or "")[:500],
            "error_message": job.error_message,
        }
