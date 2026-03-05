import os
import secrets
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field, HttpUrl

from core.database import init_db, connect, log_audit
from api.tasks import ingest_job

# ----------------------------
# Auth (API Key)
# ----------------------------
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=True)

DEFAULT_TIER = os.getenv("DEFAULT_TIER", "pro")
DEFAULT_ALLOWLIST = os.getenv("ALLOWLIST", "https://example.org/public/*")
DEFAULT_PII_MODE = os.getenv("PII_MODE", "redact")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def require_api_key(api_key: str = Depends(api_key_header)) -> Dict[str, Any]:
    """
    Verify API key against local SQLite 'users' table.
    Returns user dict {id, tier, email, api_key, created_at}
    """
    with connect() as conn:
        row = conn.execute(
            "SELECT id, email, tier, api_key, created_at FROM users WHERE api_key = ?",
            (api_key,),
        ).fetchone()

    if not row:
        raise HTTPException(status_code=403, detail="Invalid API key")

    return {
        "id": row[0],
        "email": row[1],
        "tier": row[2],
        "api_key": row[3],
        "created_at": row[4],
    }


# ----------------------------
# Models
# ----------------------------
class CreateKeyRequest(BaseModel):
    email: Optional[str] = Field(default=None, description="Optional label for the API key owner")
    tier: str = Field(default=DEFAULT_TIER, description="pro | free (extend later)")


class CreateKeyResponse(BaseModel):
    api_key: str
    tier: str
    email: Optional[str] = None


class IngestAsyncRequest(BaseModel):
    url: str = Field(..., description="URL to ingest")
    pii_mode: Optional[str] = Field(default=None, description="redact | hash (defaults to env PII_MODE)")
    allowlist: Optional[List[str]] = Field(
        default=None,
        description='Override allowlist patterns for THIS request. If omitted, uses env ALLOWLIST.',
    )


class IngestAsyncResponse(BaseModel):
    job_id: str
    status: str
    submitted_at: str


class JobStatusResponse(BaseModel):
    job_id: str
    state: str
    ready: bool
    successful: bool
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# ----------------------------
# App
# ----------------------------
app = FastAPI(title="Safe Ingestion Engine API", version="1.0.0")


@app.on_event("startup")
def startup() -> None:
    # Ensure DB exists + base tables exist
    init_db()
    with connect() as conn:
        # Users table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT,
                tier TEXT NOT NULL,
                api_key TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL
            )
            """
        )
        # Job table (optional local index; Celery still stores results in Redis)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                user_id INTEGER,
                url TEXT NOT NULL,
                state TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
            """
        )
        conn.commit()

    # Create a one-time default key if none exist (helps first run)
    with connect() as conn:
        any_user = conn.execute("SELECT id FROM users LIMIT 1").fetchone()
        if not any_user:
            api_key = secrets.token_urlsafe(32)
            conn.execute(
                "INSERT INTO users (email, tier, api_key, created_at) VALUES (?, ?, ?, ?)",
                ("local-admin", DEFAULT_TIER, api_key, utc_now_iso()),
            )
            conn.commit()
            print("\n==============================================")
            print("✅ Safe Ingestion Engine API started")
            print(f"🔑 Initial API Key (save it): {api_key}")
            print("Header to use: X-API-Key: <key>")
            print("==============================================\n")


# ----------------------------
# Routes
# ----------------------------
@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok", "time": utc_now_iso()}


@app.post("/v1/keys", response_model=CreateKeyResponse)
def create_key(req: CreateKeyRequest) -> CreateKeyResponse:
    """
    Simple local key generator (adminless).
    For production: protect this endpoint OR remove it and provision keys via admin flow/Stripe.
    """
    api_key = secrets.token_urlsafe(32)
    with connect() as conn:
        conn.execute(
            "INSERT INTO users (email, tier, api_key, created_at) VALUES (?, ?, ?, ?)",
            (req.email, req.tier, api_key, utc_now_iso()),
        )
        conn.commit()
    return CreateKeyResponse(api_key=api_key, tier=req.tier, email=req.email)


@app.post("/v1/ingest_async", response_model=IngestAsyncResponse)
def ingest_async(payload: IngestAsyncRequest, user=Depends(require_api_key)) -> IngestAsyncResponse:
    """
    Enqueue an ingestion job to Celery.
    Returns a job_id immediately.
    """
    url = payload.url.strip()
    if not (url.startswith("http://") or url.startswith("https://")):
        raise HTTPException(status_code=400, detail="URL must start with http:// or https://")

    pii_mode = (payload.pii_mode or DEFAULT_PII_MODE).strip()

    if pii_mode not in ("redact", "hash"):
        raise HTTPException(status_code=400, detail="pii_mode must be 'redact' or 'hash'")

    # Allowlist patterns for this request
    if payload.allowlist and isinstance(payload.allowlist, list) and len(payload.allowlist) > 0:
        allowlist_patterns = payload.allowlist
    else:
        allowlist_patterns = [p.strip() for p in DEFAULT_ALLOWLIST.split(",") if p.strip()]

    # Create job id
    job_id = str(uuid.uuid4())

    # Record job in DB (optional)
    with connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO jobs (id, user_id, url, state, created_at) VALUES (?, ?, ?, ?, ?)",
            (job_id, user["id"], url, "PENDING", utc_now_iso()),
        )
        conn.commit()

    # Audit: submission
    with connect() as conn:
        log_audit(conn, url, "JOB_SUBMITTED", f"user_id={user['id']} job_id={job_id}")

    # Enqueue Celery task (we force task_id = job_id so it matches)
    ingest_job.apply_async(
        args=[url, user.get("email") or f"user:{user['id']}", allowlist_patterns, pii_mode],
        task_id=job_id,
    )

    return IngestAsyncResponse(job_id=job_id, status="PENDING", submitted_at=utc_now_iso())


@app.get("/v1/jobs/{job_id}", response_model=JobStatusResponse)
def job_status(job_id: str, user=Depends(require_api_key)) -> JobStatusResponse:
    """
    Check Celery job state/result by job_id.
    """
    # Ensure user owns job (basic multi-user isolation)
    with connect() as conn:
        row = conn.execute(
            "SELECT user_id, url, state FROM jobs WHERE id = ?",
            (job_id,),
        ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Job not found")

    owner_id = row[0]
    if owner_id != user["id"]:
        raise HTTPException(status_code=403, detail="Not allowed to view this job")

    # Read Celery result
    res = ingest_job.AsyncResult(job_id)

    # Update DB state snapshot
    with connect() as conn:
        conn.execute(
            "UPDATE jobs SET state = ? WHERE id = ?",
            (res.state, job_id),
        )
        conn.commit()

    out = JobStatusResponse(
        job_id=job_id,
        state=res.state,
        ready=res.ready(),
        successful=res.successful() if res.ready() else False,
        result=None,
        error=None,
    )

    if res.ready():
        if res.successful():
            try:
                out.result = res.get(timeout=0.1)
            except Exception as e:
                out.error = f"Could not read result: {e}"
        else:
            # Task failed
            out.error = str(res.result)

    return out
