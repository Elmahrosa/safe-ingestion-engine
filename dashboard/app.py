import io
import pandas as pd
import streamlit as st
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from core.database import connect, DB  # Ensure these are imported from your core

# 1. Audit Evidence Export Section
st.subheader("📊 Audit Evidence Export")

# We assume 'audit' is your DataFrame loaded from the audit_log table
with connect() as conn:
    audit = pd.read_sql_query("SELECT * FROM audit_log ORDER BY timestamp DESC", conn)

if not audit.empty:
    # CSV Export
    csv_bytes = audit.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Download audit_log.csv",
        data=csv_bytes,
        file_name="audit_log.csv",
        mime="text/csv",
    )

    # PDF Export Function (Fixed logic)
    def audit_pdf(df):
        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=letter)
        width, height = letter
        y = height - 50
        
        # Header
        c.setFont("Helvetica-Bold", 14)
        c.drawString(50, y, "Safe Ingestion Engine — Audit Evidence")
        y -= 30
        c.setFont("Helvetica", 8) # Smaller font for better data fit

        # Table Rows
        for _, row in df.head(500).iterrows(): # Increased limit to 500
            # Safety check for missing reasons
            reason = str(row.get('reason', 'N/A'))[:60]
            line = f"{row['timestamp']} | {row['status']} | {row['url'][:50]}... | {reason}"
            
            c.drawString(50, y, line)
            y -= 12
            
            # Page Break Logic
            if y < 50:
                c.showPage()
                y = height - 50
                c.setFont("Helvetica", 8)

        c.save()
        buf.seek(0)
        return buf.getvalue()

    st.download_button(
        label="Download audit_log.pdf",
        data=audit_pdf(audit),
        file_name="audit_report.pdf",
        mime="application/pdf",
    )
else:
    st.write("No audit logs available for export.")

st.divider()

# 2. User Management (Admin) Section
st.header("👤 User Management (Admin)")

try:
    with connect() as conn:
        users_df = pd.read_sql_query("SELECT id, api_key, tier, credits FROM users", conn)

    if not users_df.empty:
        # Mask the API key for security in the UI
        users_df['api_key'] = users_df['api_key'].apply(lambda x: f"{x[:4]}...****...{x[-4:]}" if x else "N/A")
        st.table(users_df)
    else:
        st.info("No users found in the database. Run the initialization script to add a user.")
except Exception as e:
    st.error(f"Error accessing user table: {e}")
