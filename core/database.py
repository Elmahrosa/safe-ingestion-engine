import sqlite3
import hashlib
import json
import os
from urllib.parse import urlparse

DB = "data/ingestion.db"

def connect():
    """Establishes a connection to the SQLite database."""
    # Ensure the data directory exists
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    return sqlite3.connect(DB)

def init_db():
    """Initializes the database schema for SaaS operations."""
    conn = connect()
    
    # 1. User Management (SaaS Layer)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        api_key TEXT UNIQUE,
        tier TEXT DEFAULT 'free',
        credits INTEGER DEFAULT 100
    )
    """)

    # 2. Raw Ingested Data
    conn.execute("""
    CREATE TABLE IF NOT EXISTS raw_data(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_url TEXT,
        content TEXT,
        content_type TEXT,
        content_hash TEXT,
        pii_found INTEGER,
        pii_counts_json TEXT,
        scanned_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 3. Compliance Audit Log
    conn.execute("""
    CREATE TABLE IF NOT EXISTS audit_log(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        url TEXT,
        status TEXT,
        reason TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 4. Performance & Usage Metrics
    conn.execute("""
    CREATE TABLE IF NOT EXISTS request_metrics (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      url TEXT NOT NULL,
      host TEXT NOT NULL,
      status TEXT NOT NULL,
      started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      elapsed_ms INTEGER,
      bytes INTEGER,
      content_type TEXT
    )
    """)

    conn.commit()
    conn.close()

def hash_content(text):
    return hashlib.sha256(text.encode()).hexdigest()

def insert_raw(conn, url, content, ctype, pii):
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO raw_data(source_url,content,content_type,content_hash,pii_found,pii_counts_json) VALUES(?,?,?,?,?,?)",
        (url, content, ctype, hash_content(content), int(bool(pii)), json.dumps(pii))
    )
    conn.commit()
    return cursor.lastrowid

def log_audit(conn, url, status, reason):
    conn.execute(
        "INSERT INTO audit_log(url,status,reason) VALUES(?,?,?)",
        (url, status, reason)
    )
    conn.commit()

def log_metrics(conn, url, status, elapsed_ms, size_bytes, content_type):
    host = urlparse(url).netloc
    conn.execute(
        "INSERT INTO request_metrics (url, host, status, elapsed_ms, bytes, content_type) VALUES (?, ?, ?, ?, ?, ?)",
        (url, host, status, elapsed_ms, size_bytes, content_type),
    )
    conn.commit()
