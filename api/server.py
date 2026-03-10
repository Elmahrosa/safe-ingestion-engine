"""
api/server.py — FastAPI application.
Fixes:
  - Atomic credit deduction (TOCTOU race fixed)
  - SHA-256 API key lookup
  - Sheet-based credit check/deduct via SHEET_WEBHOOK_URL (Apps Script v2)
  - /v1/me endpoint added (referenced in docs.html cURL examples)
  - Default credits 20 → 10 in database.py
"""
import hashlib
import os
import sqlite3
import uuid
from datetime import datetime
from typing import Optional
import httpx
from fastapi import FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
from api.tasks import ingest_url_task
from core.database import get_db_path

app = FastAPI(title="Safe Ingestion Engine", version="1.0.0")

CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS","").split(",") if o.strip()]
app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS or ["*"], allow_methods=["*"], allow_headers=["*"])

SHEET_WEBHOOK_URL = os.getenv("SHEET_WEBHOOK_URL", "")
SHEET_API_SECRET  = os.getenv("SHEET_API_SECRET", "")

def _hash_key(raw):
    return hashlib.sha256(raw.encode()).hexdigest()

def _get_user(api_key):
    hashed = _hash_key(api_key)
    conn = sqlite3.connect(get_db_path())
    try:
        row = conn.execute("SELECT id,credits,plan,trial_active FROM users WHERE api_key_hash=?", (hashed,)).fetchone()
        return {"id":row[0],"credits":row[1],"plan":row[2],"trial_active":bool(row[3])} if row else None
    finally:
        conn.close()

def _deduct_credit_atomic(user_id):
    conn = sqlite3.connect(get_db_path(), isolation_level=None)
    try:
        conn.execute("BEGIN IMMEDIATE")
        cur = conn.execute("UPDATE users SET credits=credits-1 WHERE id=? AND credits>0", (user_id,))
        conn.execute("COMMIT")
        return cur.rowcount == 1
    except Exception:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()

def _sheet_check(api_key):
    if not SHEET_WEBHOOK_URL or not SHEET_API_SECRET:
        return None
    try:
        r = httpx.get(SHEET_WEBHOOK_URL, params={"action":"check_credits","api_key":api_key,"secret":SHEET_API_SECRET}, timeout=5.0)
        return r.json()
    except Exception:
        return None

def _sheet_deduct(api_key, amount=1):
    if not SHEET_WEBHOOK_URL or not SHEET_API_SECRET:
        return True
    try:
        r = httpx.get(SHEET_WEBHOOK_URL, params={"action":"deduct","api_key":api_key,"amount":amount,"secret":SHEET_API_SECRET}, timeout=5.0)
        return r.json().get("ok", False)
    except Exception:
        return False

class IngestRequest(BaseModel):
    url: HttpUrl
    scrub_pii: bool = True
    scrub_pii_mode: str = "redact"
    respect_robots: bool = True
    mode: str = "basic"
    timeout: int = 30

@app.post("/v1/ingest_async")
async def ingest_async(body: IngestRequest, request: Request, x_api_key: str = Header(..., alias="X-API-Key")):
    sheet = _sheet_check(x_api_key)
    if sheet is not None:
        if not sheet.get("ok"):
            raise HTTPException(401, sheet.get("error","Invalid API key"))
        if not sheet.get("has_credits", False):
            raise HTTPException(402, "No credits remaining. Top up at https://safe.teosegypt.com/#pay")
        user = {"id": 0, "credits": sheet.get("credits",0), "plan": sheet.get("plan",""), "trial_active": False}
    else:
        user = _get_user(x_api_key)
        if not user:
            raise HTTPException(401, "Invalid or expired API key.")
        if not _deduct_credit_atomic(user["id"]):
            raise HTTPException(402, "No credits remaining. Top up at https://safe.teosegypt.com/#pay")

    job_id = str(uuid.uuid4())
    ingest_url_task.delay(job_id=job_id, url=str(body.url), user_id=user["id"],
        scrub_pii=body.scrub_pii, scrub_pii_mode=body.scrub_pii_mode,
        respect_robots=body.respect_robots, timeout=min(body.timeout,120),
        tier=body.mode, api_key=x_api_key)

    credits_left = sheet.get("credits", user["credits"]) if sheet else user["credits"]
    return {"job_id": job_id, "status": "queued", "credits_remaining": credits_left}

@app.get("/v1/jobs/{job_id}")
async def get_job(job_id: str, x_api_key: str = Header(..., alias="X-API-Key")):
    sheet = _sheet_check(x_api_key)
    if sheet is not None and not sheet.get("ok"):
        raise HTTPException(401, "Invalid API key.")
    elif sheet is None and not _get_user(x_api_key):
        raise HTTPException(401, "Invalid or expired API key.")

    conn = sqlite3.connect(get_db_path())
    try:
        row = conn.execute(
            "SELECT job_id,status,url,result_content,bytes_fetched,pii_removed,latency_ms,scrub_mode,error_msg FROM jobs WHERE job_id=?",
            (job_id,)).fetchone()
    finally:
        conn.close()

    if not row:
        raise HTTPException(404, "Job not found.")

    resp = {"job_id": row[0], "status": row[1], "url": row[2]}
    if row[1] == "completed":
        resp.update({"content": row[3], "pii_redacted": row[5], "fetch_time_ms": row[6], "policy_decision": "ALLOWED"})
    elif row[1] in ("failed","blocked"):
        resp["error"] = row[8]
    return resp

@app.get("/v1/me")
async def get_me(x_api_key: str = Header(..., alias="X-API-Key")):
    """Returns current account info — used in docs examples."""
    sheet = _sheet_check(x_api_key)
    if sheet is not None:
        if not sheet.get("ok"):
            raise HTTPException(401, "Invalid API key.")
        return {"api_key": x_api_key[:12]+"...", "email": sheet.get("email",""),
                "plan": sheet.get("plan",""), "credits_remaining": sheet.get("credits",0),
                "credits_used": sheet.get("credits_used",0), "status": sheet.get("status","")}
    user = _get_user(x_api_key)
    if not user:
        raise HTTPException(401, "Invalid or expired API key.")
    return {"api_key": x_api_key[:12]+"...", "plan": user["plan"],
            "credits_remaining": user["credits"], "trial_active": user["trial_active"]}

@app.get("/v1/balance")
async def get_balance(x_api_key: str = Header(..., alias="X-API-Key")):
    return await get_me(x_api_key)

@app.get("/v1/audit")
async def get_audit(x_api_key: str = Header(..., alias="X-API-Key"),
                    limit: int = Query(default=50, le=500), page: int = Query(default=1, ge=1),
                    status: Optional[str] = Query(default=None)):
    user = _get_user(x_api_key)
    if not user:
        raise HTTPException(401, "Invalid or expired API key.")
    offset = (page-1)*limit
    where = "WHERE user_id=?"
    params = [user["id"]]
    if status and status != "all":
        where += " AND status=?"
        params.append(status)
    conn = sqlite3.connect(get_db_path())
    try:
        total = conn.execute(f"SELECT COUNT(*) FROM jobs {where}", params).fetchone()[0]
        rows  = conn.execute(f"SELECT job_id,url,status,tier,latency_ms,bytes_fetched,pii_removed,created_at FROM jobs {where} ORDER BY created_at DESC LIMIT ? OFFSET ?", params+[limit,offset]).fetchall()
    finally:
        conn.close()
    return {"total":total,"page":page,"limit":limit,"records":[
        {"job_id":r[0],"url":r[1],"status":r[2],"tier":r[3],"latency_ms":r[4],"bytes":r[5],"pii_removed":r[6],"timestamp":r[7]} for r in rows]}

@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}
