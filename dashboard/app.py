# fix_04_dashboard_sqli.py
# ─────────────────────────────────────────────────────────────────────────────
# FINDING (MEDIUM-HIGH): dashboard/app.py builds SQL by string-interpolating
# the status_filter selectbox value directly into the query string.
# While the value comes from a fixed selectbox, this pattern is fragile and
# dangerous if the input source ever changes.
#
# FILE: dashboard/app.py  — tab1 audit log block
# ─────────────────────────────────────────────────────────────────────────────

# ── REPLACE the tab1 block SQL construction with parameterized SQLAlchemy ────

PATCH = '''
with tab1:
    st.subheader("Audit Log")
    status_filter = st.selectbox(
        "Filter by status",
        ["ALL", "COMPLETED", "BLOCKED", "FAILED", "RUNNING", "RETRYING", "PENDING"]
    )

    # ── Parameterized query — no string interpolation ──────────────────────
    @st.cache_data(ttl=30, show_spinner=False)
    def _load_audit(status: str) -> pd.DataFrame:
        base_sql = text(
            "SELECT job_id, status, domain, source_url, pii_found, "
            "content_hash, security_event, created_at FROM jobs "
            + ("WHERE status = :status " if status != "ALL" else "")
            + "ORDER BY created_at DESC LIMIT 200"
        )
        with get_engine().connect() as conn:
            params = {"status": status} if status != "ALL" else {}
            return pd.read_sql(base_sql, conn, params=params)

    df = _load_audit(status_filter)
    st.dataframe(df, use_container_width=True)

    csv = df.to_csv(index=False).encode()
    st.download_button("⬇️ Export CSV", csv, "audit_log.csv", "text/csv")
'''

print("Fix 04: Replace the `with tab1:` block in dashboard/app.py with PATCH above.")
