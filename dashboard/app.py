import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
st.subheader("Audit Evidence Export")

csv_bytes = audit.to_csv(index=False).encode("utf-8")
st.download_button(
    "Download audit_log.csv",
    data=csv_bytes,
    file_name="audit_log.csv",
    mime="text/csv",
)

def audit_pdf(df):
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    width, height = letter
    y = height - 50
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y, "Safe Ingestion Engine — Audit Evidence")
    y -= 30
    c.setFont("Helvetica", 9)

    for _, row in df.head(200).iterrows():
        line = f"{row['timestamp']} | {row['status']} | {row['url']} | {str(row.get('reason',''))[:80]}"
        c.drawString(50, y, line)
        y -= 12
        if y < 60:
            c.showPage()
            y = height - 50
            c.setFont("Helvetica", 9)

    c.save()
    buf.seek(0)
    return buf.getvalue()

st.download_button(
    "Download audit_log.pdf",
    data=audit_pdf(audit),
    file_name="audit_log.pdf",
    mime="application/pdf",
)
