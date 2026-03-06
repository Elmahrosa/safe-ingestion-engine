import io
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

DB_PATH = Path("data/ingestion.db")

st.set_page_config(page_title="Safe Ingestion Dashboard", layout="wide")
st.title("🛡️ Safe Ingestion Dashboard (Read-Only)")

if not DB_PATH.exists():
    st.warning("Database not found yet. Run the scraper/API once to create data/ingestion.db")
    st.stop()

def get_conn():
    return sqlite3.connect(str(DB_PATH))

def table_exists(conn, name: str) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (name,),
    ).fetchone()
    return row is not None

def audit_pdf(audit_df: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    width, height = letter
    x = 40
    y = height - 50

    c.setFont("Helvetica-Bold", 14)
    c.drawString(x, y, "Safe Ingestion Engine — Audit Evidence Export")
    y -= 20
    c.setFont("Helvetica", 10)
    c.drawString(x, y, f"Generated at: {datetime.utcnow().isoformat()}Z")
    y -= 30

    c.setFont("Helvetica-Bold", 10)
    c.drawString(x, y, "timestamp")
    c.drawString(x + 140, y, "status")
    c.drawString(x + 260, y, "url")
    y -= 14
    c.setFont("Helvetica", 9)

    # Print last 100 lines max
    for _, r in audit_df.head(100).iterrows():
        if y < 60:
            c.showPage()
            y = height - 50
            c.setFont("Helvetica", 9)

        ts = str(r.get("timestamp", ""))[:19]
        status = str(r.get("status", ""))[:20]
        url = str(r.get("url", ""))[:70]
        reason = str(r.get("reason", ""))[:90]

        c.drawString(x, y, ts)
        c.drawString(x + 140, y, status)
        c.drawString(x + 260, y, url)
        y -= 12
        c.setFillGray(0.2)
        c.drawString(x + 40, y, f"reason: {reason}")
        c.setFillGray(0)
        y -= 14

    c.save()
    buf.seek(0)
    return buf.read()

with get_conn() as conn:
    # Audit Log
    st.subheader("Audit Log")
    if not table_exists(conn, "audit_log"):
        st.error("Missing table: audit_log (run init_db / first run).")
    else:
        audit = pd.read_sql_query(
            "SELECT timestamp, status, url, reason FROM audit_log ORDER BY timestamp DESC LIMIT 500",
            conn,
        )
        st.dataframe(audit, height=320, use_container_width=True)

        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                "⬇️ Export Audit CSV",
                data=audit.to_csv(index=False).encode("utf-8"),
                file_name="audit_log.csv",
                mime="text/csv",
            )
        with col2:
            st.download_button(
                "⬇️ Export Audit PDF",
                data=audit_pdf(audit),
                file_name="audit_evidence.pdf",
                mime="application/pdf",
            )

    # Recent Ingestions
    st.subheader("Recent Ingestions")
    if not table_exists(conn, "raw_data"):
        st.error("Missing table: raw_data (run a successful ingestion).")
    else:
        raw = pd.read_sql_query(
            "SELECT scanned_at, source_url, content_type, content_hash, pii_found FROM raw_data ORDER BY scanned_at DESC LIMIT 200",
            conn,
        )
        st.dataframe(raw, height=320, use_container_width=True)

st.caption("Dashboard is read-only. Data comes from SQLite at data/ingestion.db")
