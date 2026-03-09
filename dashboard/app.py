"""
dashboard/app.py — Streamlit monitoring dashboard.
Fixes:
  - Admin section exposed all user data to anyone → password-protected
  - request_metrics table had no view → Metrics tab with KPI cards added
  - PDF export was a blank page → now exports actual audit table via ReportLab
"""

import io
import os
import sqlite3
from datetime import datetime

import pandas as pd
import streamlit as st

# ReportLab for working PDF export
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
    )
    _REPORTLAB_OK = True
except ImportError:
    _REPORTLAB_OK = False

from core.database import get_db_path

ADMIN_PASSWORD = os.getenv("DASHBOARD_ADMIN_PASSWORD", "")

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Safe Ingestion Engine",
    page_icon="🛡",
    layout="wide",
)


# ── DB helpers ─────────────────────────────────────────────────────────────────

@st.cache_data(ttl=30)
def load_audit(limit: int = 500) -> pd.DataFrame:
    conn = sqlite3.connect(get_db_path())
    df = pd.read_sql_query(
        f"""
        SELECT job_id, url, status, tier, latency_ms, bytes_fetched,
               pii_removed, timestamp
        FROM audit_log
        ORDER BY timestamp DESC
        LIMIT {limit}
        """,
        conn,
    )
    conn.close()
    return df


@st.cache_data(ttl=30)
def load_metrics() -> pd.DataFrame:
    conn = sqlite3.connect(get_db_path())
    df = pd.read_sql_query(
        """
        SELECT recorded_at, latency_ms, bytes_fetched, pii_removed, tier, status
        FROM request_metrics
        ORDER BY recorded_at DESC
        LIMIT 1000
        """,
        conn,
    )
    conn.close()
    return df


@st.cache_data(ttl=60)
def load_users() -> pd.DataFrame:
    conn = sqlite3.connect(get_db_path())
    df = pd.read_sql_query(
        "SELECT id, email, credits, plan, trial_active, created_at FROM users",
        conn,
    )
    conn.close()
    return df


# ── PDF export ─────────────────────────────────────────────────────────────────

def _build_pdf(df: pd.DataFrame) -> bytes:
    """
    Build a real PDF from the audit DataFrame using ReportLab platypus.
    Fix: was previously returning a blank page.
    """
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=1 * cm, leftMargin=1 * cm)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph("Safe Ingestion Engine — Audit Report", styles["Title"]))
    elements.append(Paragraph(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}", styles["Normal"]))
    elements.append(Spacer(1, 0.5 * cm))

    cols = ["job_id", "url", "status", "tier", "latency_ms", "pii_removed", "timestamp"]
    display_cols = [c for c in cols if c in df.columns]

    table_data = [display_cols] + [
        [str(row[c])[:40] for c in display_cols] for _, row in df.head(200).iterrows()
    ]

    tbl = Table(table_data, repeatRows=1)
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1a2e")),
        ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
        ("FONTSIZE",   (0, 0), (-1, 0), 8),
        ("FONTSIZE",   (0, 1), (-1, -1), 7),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f0f0f0")]),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    elements.append(tbl)
    doc.build(elements)
    return buf.getvalue()


# ── Sidebar / Auth ─────────────────────────────────────────────────────────────

st.sidebar.title("🛡 Safe Ingestion")
st.sidebar.caption("Monitoring Dashboard")

tab_selection = st.sidebar.radio(
    "View",
    ["📋 Audit Log", "📊 Metrics", "🔒 Admin"],
    index=0,
)


# ── Tab: Audit Log ─────────────────────────────────────────────────────────────

if tab_selection == "📋 Audit Log":
    st.title("📋 Audit Log")

    audit_df = load_audit()

    if audit_df.empty:
        st.info("No audit records yet.")
    else:
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Requests", len(audit_df))
        col2.metric("Completed", int((audit_df["status"] == "completed").sum()))
        col3.metric("Blocked",   int((audit_df["status"] == "blocked").sum()))
        col4.metric("Failed",    int((audit_df["status"] == "failed").sum()))

        status_filter = st.selectbox("Filter by status", ["all", "completed", "blocked", "failed"])
        if status_filter != "all":
            filtered = audit_df[audit_df["status"] == status_filter]
        else:
            filtered = audit_df

        st.dataframe(filtered, use_container_width=True)

        # CSV download
        csv_data = filtered.to_csv(index=False).encode()
        st.download_button("⬇ Download CSV", csv_data, "audit_log.csv", "text/csv")

        # PDF download
        if _REPORTLAB_OK:
            pdf_data = _build_pdf(filtered)
            st.download_button("⬇ Download PDF", pdf_data, "audit_report.pdf", "application/pdf")
        else:
            st.warning("Install reportlab to enable PDF export: `pip install reportlab`")


# ── Tab: Metrics ──────────────────────────────────────────────────────────────

elif tab_selection == "📊 Metrics":
    st.title("📊 Performance Metrics")

    metrics_df = load_metrics()

    if metrics_df.empty:
        st.info("No metrics recorded yet.")
    else:
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Requests Tracked", len(metrics_df))
        col2.metric(
            "Avg Latency (ms)",
            f"{metrics_df['latency_ms'].dropna().mean():.0f}" if not metrics_df["latency_ms"].dropna().empty else "—",
        )
        col3.metric(
            "Total Bytes Fetched",
            f"{metrics_df['bytes_fetched'].sum() / 1024:.1f} KB",
        )
        col4.metric(
            "Total PII Removed",
            int(metrics_df["pii_removed"].sum()),
        )

        st.subheader("Latency over time")
        if "recorded_at" in metrics_df.columns and "latency_ms" in metrics_df.columns:
            chart_df = metrics_df[["recorded_at", "latency_ms"]].dropna()
            chart_df["recorded_at"] = pd.to_datetime(chart_df["recorded_at"])
            chart_df = chart_df.set_index("recorded_at").sort_index()
            st.line_chart(chart_df)

        st.subheader("Tier breakdown")
        tier_counts = metrics_df["tier"].value_counts()
        st.bar_chart(tier_counts)

        st.subheader("Raw Metrics")
        st.dataframe(metrics_df, use_container_width=True)


# ── Tab: Admin (password-protected) ──────────────────────────────────────────

elif tab_selection == "🔒 Admin":
    st.title("🔒 Admin")

    if not ADMIN_PASSWORD:
        st.warning(
            "Admin tab is disabled. Set `DASHBOARD_ADMIN_PASSWORD` env var to enable it."
        )
        st.stop()

    if "admin_authed" not in st.session_state:
        st.session_state.admin_authed = False

    if not st.session_state.admin_authed:
        pwd = st.text_input("Enter admin password", type="password")
        if st.button("Login"):
            if pwd == ADMIN_PASSWORD:
                st.session_state.admin_authed = True
                st.rerun()
            else:
                st.error("Incorrect password.")
        st.stop()

    # Authenticated admin view
    st.success("✅ Authenticated")

    st.subheader("All Users")
    users_df = load_users()
    st.dataframe(users_df, use_container_width=True)

    if st.button("🔄 Refresh"):
        load_users.clear()
        load_audit.clear()
        load_metrics.clear()
        st.rerun()
