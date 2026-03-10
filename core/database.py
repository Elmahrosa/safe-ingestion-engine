"""
core/database.py — SQLite schema bootstrap + helper functions.
FIX: Default trial credits changed from 20 → 10 to match Apps Script + website.
"""
import os
import sqlite3
from datetime import datetime

DATA_DIR = os.getenv("DATA_DIR", "data")
DB_NAME  = "safe_ingestion.db"

def get_db_path() -> str:
    os.makedirs(DATA_DIR, exist_ok=True)
    return os.path.join(DATA_DIR, DB_NAME)

def init_db() -> None:
    conn = sqlite3.connect(get_db_path())
    try:
        conn.executescript("""
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                email         TEXT    UNIQUE NOT NULL,
                api_key_hash  TEXT    UNIQUE NOT NULL,
                credits       INTEGER NOT NULL DEFAULT 10,
                plan          TEXT    NOT NULL DEFAULT 'trial',
                trial_active  INTEGER NOT NULL DEFAULT 1,
                created_at    TEXT    NOT NULL,
                updated_at    TEXT    NOT NULL
            );
            CREATE TABLE IF NOT EXISTS jobs (
                job_id          TEXT    PRIMARY KEY,
                user_id         INTEGER NOT NULL,
                url             TEXT    NOT NULL,
                status          TEXT    NOT NULL DEFAULT 'queued',
                result_content  TEXT,
                bytes_fetched   INTEGER,
                pii_removed     INTEGER DEFAULT 0,
                latency_ms      INTEGER,
                scrub_mode      TEXT,
                tier            TEXT    DEFAULT 'basic',
                error_msg       TEXT,
                created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
                updated_at      TEXT
            );
            CREATE TABLE IF NOT EXISTS audit_log (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id        TEXT    NOT NULL,
                user_id       INTEGER NOT NULL,
                url           TEXT    NOT NULL,
                status        TEXT    NOT NULL,
                tier          TEXT,
                reason        TEXT,
                latency_ms    INTEGER,
                bytes_fetched INTEGER,
                pii_removed   INTEGER DEFAULT 0,
                timestamp     TEXT    NOT NULL DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS request_metrics (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id        TEXT    NOT NULL,
                user_id       INTEGER NOT NULL,
                latency_ms    INTEGER,
                bytes_fetched INTEGER,
                pii_removed   INTEGER DEFAULT 0,
                tier          TEXT,
                status        TEXT,
                recorded_at   TEXT    NOT NULL DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS raw_content (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id     TEXT    NOT NULL,
                user_id    INTEGER NOT NULL,
                url        TEXT    NOT NULL,
                content    TEXT,
                stored_at  TEXT    NOT NULL DEFAULT (datetime('now'))
            );
            CREATE INDEX IF NOT EXISTS idx_jobs_user_id    ON jobs(user_id);
            CREATE INDEX IF NOT EXISTS idx_audit_user_id   ON audit_log(user_id);
            CREATE INDEX IF NOT EXISTS idx_metrics_user_id ON request_metrics(user_id);
        """)
        conn.commit()
    finally:
        conn.close()

def log_audit(conn, *, job_id, user_id, url, status, tier="basic", reason=None, latency_ms=None, bytes_fetched=None, pii_removed=0):
    conn.execute(
        "INSERT INTO audit_log (job_id,user_id,url,status,tier,reason,latency_ms,bytes_fetched,pii_removed,timestamp) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (job_id, user_id, url, status, tier, reason, latency_ms, bytes_fetched, pii_removed, datetime.utcnow().isoformat()),
    )
    conn.commit()

def log_metrics(conn, *, job_id, user_id, latency_ms=None, bytes_fetched=None, pii_removed=0, tier="basic", status="completed"):
    conn.execute(
        "INSERT INTO request_metrics (job_id,user_id,latency_ms,bytes_fetched,pii_removed,tier,status,recorded_at) VALUES (?,?,?,?,?,?,?,?)",
        (job_id, user_id, latency_ms, bytes_fetched, pii_removed, tier, status, datetime.utcnow().isoformat()),
    )
    conn.commit()

def insert_raw(conn, *, job_id, user_id, url, content):
    conn.execute(
        "INSERT INTO raw_content (job_id,user_id,url,content,stored_at) VALUES (?,?,?,?,?)",
        (job_id, user_id, url, content, datetime.utcnow().isoformat()),
    )
    conn.commit()
