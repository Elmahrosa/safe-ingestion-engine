import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st

DB_PATH = Path("data/ingestion.db")

st.set_page_config(page_title="Safe Ingestion Dashboard", layout="wide")
st.title("Safe Ingestion Dashboard (Read-Only)")

if not DB_PATH.exists():
    st.warning("Database not found yet. Run the scraper once to create data/ingestion.db")
    st.stop()

conn = sqlite3.connect(str(DB_PATH))

st.subheader("Audit Log")
try:
    audit = pd.read_sql_query(
        "SELECT timestamp, status, url, reason FROM audit_log ORDER BY timestamp DESC LIMIT 500",
        conn,
    )
    st.dataframe(audit, use_container_width=True, height=350)
except Exception as e:
    st.error(f"Could not read audit_log: {e}")

st.subheader("Recent Ingestions")
try:
    raw = pd.read_sql_query(
        "SELECT scanned_at, source_url, content_type, content_hash, pii_found FROM raw_data ORDER BY scanned_at DESC LIMIT 200",
        conn,
    )
    st.dataframe(raw, use_container_width=True, height=350)
except Exception as e:
    st.error(f"Could not read raw_data: {e}")

conn.close()
