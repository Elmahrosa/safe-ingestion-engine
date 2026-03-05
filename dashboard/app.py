import sqlite3
import io
import pandas as pd
import streamlit as st
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

DB_PATH = Path("data/ingestion.db")
st.set_page_config(page_title="Safe Ingestion Dashboard", layout="wide")
st.title("🛡️ Safe Ingestion Dashboard")

if not DB_PATH.exists():
    st.warning("Database not found. Run a crawl to begin.")
    st.stop()

def get_conn():
    return sqlite3.connect(str(DB_PATH))

# --- Audit Evidence Section ---
st.subheader("Audit Log & Evidence")
with get_conn() as conn:
    audit = pd.read_sql_query("SELECT * FROM audit_log ORDER BY timestamp DESC", conn)

if not audit.empty:
    st.dataframe(audit, use_container_width=True)
    
    col1, col2 = st.columns(2)
    with col1:
        st.download_button("Download CSV", audit.to_csv(index=False), "audit.csv", "text/csv")
    with col2:
        # Simple PDF Generator
        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=letter)
        c.drawString(100, 750, "Safe Ingestion Audit Report")
        c.save()
        st.download_button("Download PDF Report", buf.getvalue(), "audit.pdf", "application/pdf")

# --- Admin Section ---
st.divider()
st.subheader("👤 User Credits (Admin)")
with get_conn() as conn:
    try:
        users = pd.read_sql_query("SELECT user_name, tier, credits FROM users", conn)
        st.table(users)
    except:
        st.info("No users table found yet.")
