import os
import time
import uuid
import sqlite3
from pathlib import Path
from urllib.parse import urlparse

import requests

DB_PATH = Path(os.getenv("DB_PATH", "data/ingestion.db"))

def _conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("""
    CREATE TABLE IF NOT EXISTS audit_log(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      timestamp TEXT,
      status TEXT,
      url TEXT,
      reason TEXT
    )
    """)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS request_metrics(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      timestamp TEXT,
      url TEXT,
      host TEXT,
      status TEXT,
      elapsed_ms INTEGER,
      bytes INTEGER
    )
    """)
    conn.commit()
    return conn

def log_audit(url: str, status: str, reason: str):
    with _conn() as conn:
        conn.execute(
            "INSERT INTO audit_log(timestamp,status,url,reason) VALUES(datetime('now'),?,?,?)",
            (status, url, reason),
        )
        conn.commit()

def log_metrics(url: str, status: str, elapsed_ms: int, size_bytes: int):
    host = urlparse(url).netloc
    with _conn() as conn:
        conn.execute(
            "INSERT INTO request_metrics(timestamp,url,host,status,elapsed_ms,bytes) VALUES(datetime('now'),?,?,?,?,?)",
            (url, host, status, elapsed_ms, size_bytes),
        )
        conn.commit()

def policy_check(url: str) -> tuple[bool, str, str]:
    # SAFE DEFAULT: allow only if not obviously dangerous scheme
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return (False, "BLOCKED_POLICY", "Unsupported URL scheme")
    return (True, "ALLOWED_POLICY", "Allowed by default policy")

from api.celery_app import celery

@celery.task(bind=True)
def ingest_url(self, url: str):
    allowed, status, reason = policy_check(url)
    if not allowed:
        log_audit(url, status, reason)
        return {"ok": False, "status": status, "reason": reason}

    start = time.time()
    try:
        r = requests.get(url, timeout=20, headers={"User-Agent": os.getenv("USER_AGENT", "SafeIngestion/1.0")})
        elapsed_ms = int((time.time() - start) * 1000)
        size_bytes = len(r.content or b"")
        ok_status = "FETCH_OK" if r.ok else f"HTTP_{r.status_code}"
        log_metrics(url, ok_status, elapsed_ms, size_bytes)

        if not r.ok:
            log_audit(url, "BLOCKED_HTTP", f"HTTP status {r.status_code}")
            return {"ok": False, "status": "BLOCKED_HTTP", "reason": f"HTTP {r.status_code}"}

        log_audit(url, "INGESTED", "Fetched successfully")
        return {
            "ok": True,
            "url": url,
            "content_type": r.headers.get("Content-Type", ""),
            "size_bytes": size_bytes,
            "latency_ms": elapsed_ms,
            "audit_ref": str(uuid.uuid4()),
        }
    except Exception as e:
        elapsed_ms = int((time.time() - start) * 1000)
        log_metrics(url, "ERROR", elapsed_ms, 0)
        log_audit(url, "ERROR", str(e))
        return {"ok": False, "status": "ERROR", "reason": str(e)}
