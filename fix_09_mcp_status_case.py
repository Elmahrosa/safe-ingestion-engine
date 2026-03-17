# fix_09_mcp_status_case.py
# ─────────────────────────────────────────────────────────────────────────────
# FINDING (CRITICAL for MCP users): mcp_server.py polls for
#     job["status"] == "completed"
# but JobStatus.COMPLETED = "COMPLETED" (uppercase).
# The poll loop NEVER exits on success — it always times out.
# Same bug for "failed" check.
#
# FILE: mcp_server.py  — ingest_url tool handler
# ─────────────────────────────────────────────────────────────────────────────

PATCH = '''
        if name == "ingest_url":
            url = arguments.get("url", "")
            if not url:
                return [types.TextContent(type="text", text="Error: url required")]
            payload = {"url": url}
            if k := arguments.get("idempotency_key"):
                payload["idempotency_key"] = k
            r = await client.post("/v1/ingest_async", json=payload)
            if r.status_code == 402:
                return [types.TextContent(type="text", text="No credits. Top up at https://safe.teosegypt.com")]
            if r.status_code != 200:
                return [types.TextContent(type="text", text=f"Error {r.status_code}: {r.text}")]
            job_id = r.json()["job_id"]
            deadline = time.monotonic() + 60
            while time.monotonic() < deadline:
                await asyncio.sleep(2)
                poll = await client.get(f"/v1/jobs/{job_id}")
                if poll.status_code != 200:
                    continue
                job = poll.json()
                status = job["status"].upper()           # ← normalise case
                if status == "COMPLETED":
                    return [types.TextContent(type="text", text=(
                        f"Ingestion complete | Job: {job_id} | PII redacted: {job.get('pii_found',0)}\\n\\n"
                        f"{job.get('result_excerpt','')}"
                    ))]
                if status == "BLOCKED":
                    return [types.TextContent(type="text", text=f"Blocked by policy: {job.get('error_message')}")]
                if status == "FAILED":
                    return [types.TextContent(type="text", text=f"Failed: {job.get('error_message')}")]
                # PENDING / RUNNING / RETRYING → keep polling
            return [types.TextContent(type="text", text=f"Timeout. Poll manually: get_job(job_id=\\'{job_id}\\')")]
'''

# Same fix applies to the get_job tool — purely cosmetic there since it just
# passes status through to the user, but normalise for display consistency.

print("Fix 09: In mcp_server.py, replace the `if name == 'ingest_url':` block")
print("with PATCH above.")
print()
print("Key changes:")
print("  job['status'].upper() normalises COMPLETED/completed/Completed")
print("  BLOCKED status is now also handled (returns reason instead of timing out)")
