"""
Safe Ingestion Engine — Streamlit Dashboard
Run: streamlit run dashboard/app.py
"""
from __future__ import annotations

import os
import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text

# ── Config ────────────────────────────────────────────────────────────────────
DB_URL = os.environ.get("DATABASE_URL", "sqlite:///./data/jobs.db")
ADMIN_PASSWORD = os.environ.get("DASHBOARD_ADMIN_PASSWORD", "")

st.set_page_config(
    page_title="Safe Ingestion Engine",
    page_icon="🛡️",
    layout="wide",
)

# ── Auth ──────────────────────────────────────────────────────────────────────
if ADMIN_PASSWORD:
    pwd = st.sidebar.text_input("Admin password", type="password")
    if pwd != ADMIN_PASSWORD:
        st.warning("Enter admin password to continue.")
        st.stop()

# ── DB helper ─────────────────────────────────────────────────────────────────
@st.cache_resource
def get_engine():
    return create_engine(DB_URL)

def query(sql: str) -> pd.DataFrame:
    with get_engine().connect() as conn:
        return pd.read_sql(text(sql), conn)

# ── Header ────────────────────────────────────────────────────────────────────
st.title("🛡️ Safe Ingestion Engine")
st.caption("Compliance-first web data ingestion — audit dashboard")

# ── KPI row ───────────────────────────────────────────────────────────────────
try:
    df_all = query("SELECT status, pii_found, content_hash FROM jobs")
    total       = len(df_all)
    completed   = len(df_all[df_all.status == "COMPLETED"])
    blocked     = len(df_all[df_all.status == "BLOCKED"])
    failed      = len(df_all[df_all.status == "FAILED"])
    pii_total   = int(df_all.pii_found.sum())
    deduped     = total - df_all.content_hash.nunique()

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Total Jobs",      total)
    c2.metric("Completed",       completed)
    c3.metric("Blocked",         blocked,   delta_color="inverse")
    c4.metric("Failed",          failed,    delta_color="inverse")
    c5.metric("PII Redacted",    pii_total)
    c6.metric("Duplicates",      deduped)

except Exception as e:
    st.error(f"DB error: {e}")
    st.stop()

st.divider()

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["📋 Audit Log", "📊 Metrics", "🌐 Domains"])

with tab1:
    st.subheader("Audit Log")
    status_filter = st.selectbox(
        "Filter by status",
        ["ALL", "COMPLETED", "BLOCKED", "FAILED", "RUNNING", "RETRYING", "PENDING"]
    )
    sql = "SELECT job_id, status, domain, source_url, pii_found, content_hash, security_event, created_at FROM jobs"
    if status_filter != "ALL":
        sql += f" WHERE status = '{status_filter}'"
    sql += " ORDER BY created_at DESC LIMIT 200"
    df = query(sql)
    st.dataframe(df, use_container_width=True)

    # Export
    csv = df.to_csv(index=False).encode()
    st.download_button("⬇️ Export CSV", csv, "audit_log.csv", "text/csv")

with tab2:
    st.subheader("Job Throughput")
    try:
        df_time = query(
            "SELECT date(created_at) as day, status, count(*) as count "
            "FROM jobs GROUP BY day, status ORDER BY day DESC LIMIT 90"
        )
        if not df_time.empty:
            pivot = df_time.pivot_table(
                index="day", columns="status", values="count", fill_value=0
            )
            st.bar_chart(pivot)

        st.subheader("PII Tokens by Domain")
        df_pii = query(
            "SELECT domain, sum(pii_found) as total_pii, count(*) as jobs "
            "FROM jobs GROUP BY domain ORDER BY total_pii DESC LIMIT 20"
        )
        st.dataframe(df_pii, use_container_width=True)

    except Exception as e:
        st.error(f"Chart error: {e}")

with tab3:
    st.subheader("Domain Statistics")
    try:
        df_dom = query(
            "SELECT domain, "
            "count(*) as total, "
            "sum(case when status='COMPLETED' then 1 else 0 end) as completed, "
            "sum(case when status='BLOCKED' then 1 else 0 end) as blocked, "
            "sum(case when status='FAILED' then 1 else 0 end) as failed, "
            "sum(pii_found) as pii_found, "
            "max(updated_at) as last_crawled "
            "FROM jobs GROUP BY domain ORDER BY total DESC"
        )
        st.dataframe(df_dom, use_container_width=True)
    except Exception as e:
        st.error(f"Domain error: {e}")