"""
api/server.py — FastAPI application.

Security hardening applied:
  - Job IDs: full UUID4 (was short hex → enumerable)
  - IDOR fix: GET /jobs/{id} checks job.user_id == authenticated user
  - Rate limiting: slowapi 5/min per IP on ingest endpoint
  - API keys: SHA-256 hashed (existing, confirmed)
  - Atomic credit deduction: UPDATE WHERE credits>0 (existing, confirmed)
  - CORS: explicit origins from settings (not *)
"""

import hashlib
import sqlite3
import uuid
from datetime import datetime
from typing import Optional

import httpx
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from api.tasks import ingest_url_task
from core.config import settings
from core.database import get_db_path

# ── Rate limiter ──────────────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="Safe Ingestion Engine", version="1.0.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_list(),
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

SHEET_WEBHOOK_URL = settings.sheet_webhook_url
SHEET_API_SECRET  = settings.sheet_api_secret


# ── Auth helpers ──────────────────────────────────────────────────────────────

def _hash_key(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def _get_user(api_key: str) -> Optional[dict]:
    hashed = _hash_key(api_key)
    conn = sqlite3.connect(get_db_path())
    try:
        row = conn.execute(
            "SELECT id, credits, plan, trial_active FROM users WHERE api_key_hash=?",
            (hashed,),
        ).fetchone()
        return {"id": row[0], "credits": row[1], "plan": row[2], "trial_active": bool(row[3])} if row else None
    finally:
        conn.close()


def _deduct_credit_atomic(user_id: int) -> bool:
    """Atomic credit deduction — prevents TOCTOU race."""
    conn = sqlite3.connect(get_db_path(), isolation_level=None)
    try:
        conn.execute("BEGIN IMMEDIATE")
        cur = conn.execute(
            "UPDATE users SET credits=credits-1 WHERE id=? AND credits>0",
            (user_id,),
        )
        conn.execute("COMMIT")
        return cur.rowcount == 1
    except Exception:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()


def _sheet_check(api_key: str) -> Optional[dict]:
    if not SHEET_WEBHOOK_URL or not SHEET_API_SECRET:
        return None
    try:
        r = httpx.get(
            SHEET_WEBHOOK_URL,
            params={"action": "check_credits", "api_key": api_key, "secret": SHEET_API_SECRET},
            timeout=5.0,
        )
        return r.json()
    except Exception:
        return None


def _sheet_deduct(api_key: str, amount: int = 1) -> bool:
    if not SHEET_WEBHOOK_URL or not SHEET_API_SECRET:
        return True
    try:
        r = httpx.get(
            SHEET_WEBHOOK_URL,
            params={"action": "deduct", "api_key": api_key, "amount": amount, "secret": SHEET_API_SECRET},
            timeout=5.0,
        )
        return r.json().get("ok", False)
    except Exception:
        return False


# ── Request models ────────────────────────────────────────────────────────────

class IngestRequest(BaseModel):
    url: HttpUrl
    scrub_pii: bool = True
    scrub_pii_mode: str = "redact"
    respect_robots: bool = True
    mode: str = "basic"
    timeout: int = 30


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}


@app.post("/v1/ingest_async")
@limiter.limit("5/minute")
async def ingest_async(
    body: IngestRequest,
    request: Request,
    x_api_key: str = Header(..., alias="X-API-Key"),
):
    # 1. Authenticate
    sheet = _sheet_check(x_api_key)
    if sheet is not None:
        if not sheet.get("ok"):
            raise HTTPException(401, sheet.get("error", "Invalid API key"))
        if not sheet.get("has_credits", False):
            raise HTTPException(402, "No credits remaining. Top up at https://safe.teosegypt.com/#pricing")
    else:
        user = _get_user(x_api_key)
        if not user:
            raise HTTPException(401, "Invalid or expired API key.")
        if user["credits"] <= 0:
            raise HTTPException(402, "No credits remaining. Top up at https://safe.teosegypt.com/#pricing")

    # 2. Deduct credit atomically
    if sheet is not None:
        if not _sheet_deduct(x_api_key):
            raise HTTPException(402, "Credit deduction failed.")
        user_id = 0
    else:
        if not _deduct_credit_atomic(user["id"]):
            raise HTTPException(402, "No credits remaining.")
        user_id = user["id"]

    # 3. Create job with full UUID4 (not enumerable)
    job_id = str(uuid.uuid4())
    conn = sqlite3.connect(get_db_path())
    try:
        conn.execute(
            """INSERT INTO jobs (job_id, user_id, status, url, created_at, updated_at)
               VALUES (?, ?, 'queued', ?, ?, ?)""",
            (job_id, user_id, str(body.url), datetime.utcnow().isoformat(), datetime.utcnow().isoformat()),
        )
        conn.commit()
    finally:
        conn.close()

    # 4. Enqueue
    ingest_url_task.delay(
        job_id=job_id,
        url=str(body.url),
        user_id=user_id,
        scrub_pii=body.scrub_pii,
        scrub_pii_mode=body.scrub_pii_mode,
        respect_robots=body.respect_robots,
        timeout=min(body.timeout, 30),
        tier=user["plan"] if sheet is None else "sheet",
        api_key=x_api_key,
    )

    return {"job_id": job_id, "status": "queued"}


@app.get("/v1/jobs/{job_id}")
async def get_job(
    job_id: str,
    request: Request,
    x_api_key: str = Header(..., alias="X-API-Key"),
):
    # 1. Authenticate
    sheet = _sheet_check(x_api_key)
    if sheet is not None and not sheet.get("ok"):
        raise HTTPException(401, "Invalid API key.")

    user = _get_user(x_api_key) if sheet is None else {"id": 0}
    if not user and sheet is None:
        raise HTTPException(401, "Invalid or expired API key.")

    # 2. Fetch job
    conn = sqlite3.connect(get_db_path())
    try:
        row = conn.execute(
            """SELECT user_id, job_id, status, url, result_content,
                      bytes_fetched, pii_removed, latency_ms, scrub_mode, error_msg
               FROM jobs WHERE job_id=?""",
            (job_id,),
        ).fetchone()
    finally:
        conn.close()

    # 3. IDOR protection — always return 404 if not found OR not owned
    # Never reveal whether a job exists to an unauthorized caller
    if not row or row[0] != user["id"]:
        raise HTTPException(404, "Job not found.")

    # 4. Return result
    resp = {"job_id": row[1], "status": row[2], "url": row[3]}
    if row[2] == "completed":
        resp.update({
            "content": row[4],
            "pii_redacted": row[6],
            "fetch_time_ms": row[7],
            "policy_decision": "ALLOWED",
        })
    elif row[2] in ("failed", "blocked"):
        resp["error"] = row[9]
    return resp


@app.get("/v1/me")
async def me(x_api_key: str = Header(..., alias="X-API-Key")):
    user = _get_user(x_api_key)
    if not user:
        raise HTTPException(401, "Invalid API key.")
    return {
        "credits": user["credits"],
        "plan": user["plan"],
        "trial_active": user["trial_active"],
    }
