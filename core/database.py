import sqlite3
import hashlib
import json

DB="data/ingestion.db"

def connect():
    return sqlite3.connect(DB)

def init_db(conn.execute("""
CREATE TABLE IF NOT EXISTS request_metrics (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  url TEXT NOT NULL,
  host TEXT NOT NULL,
  status TEXT NOT NULL,
  started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  elapsed_ms INTEGER,
  bytes INTEGER,
  content_type TEXT
):

    conn=connect()

    conn.execute("""
    CREATE TABLE IF NOT EXISTS raw_data(
        id INTEGER PRIMARY KEY,
        source_url TEXT,
        content TEXT,
        content_type TEXT,
        content_hash TEXT,
        pii_found INTEGER,
        pii_counts_json TEXT,
        scanned_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS audit_log(
        id INTEGER PRIMARY KEY,
        url TEXT,
        status TEXT,
        reason TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()

def hash_content(text):
    return hashlib.sha256(text.encode()).hexdigest()

def insert_raw(conn,url,content,ctype,pii):

    conn.execute(
    "INSERT INTO raw_data(source_url,content,content_type,content_hash,pii_found,pii_counts_json) VALUES(?,?,?,?,?,?)",
    (url,content,ctype,hash_content(content),bool(pii),json.dumps(pii))
    )

    conn.commit()

def log_audit(conn,url,status,reason):

    conn.execute(
    "INSERT INTO audit_log(url,status,reason) VALUES(?,?,?)",
    (url,status,reason)
    )

    conn.commit()
