@app.get("/v1/jobs/{job_id}")
async def get_job(job_id: str, x_api_key: str = Header(..., alias="X-API-Key")):
    # 1. Authenticate user
    sheet = _sheet_check(x_api_key)
    if sheet is not None and not sheet.get("ok"):
        raise HTTPException(401, "Invalid API key.")
    
    # Get the user ID from the local DB if not using sheet
    user = _get_user(x_api_key) if sheet is None else {"id": 0} 
    if not user and sheet is None:
        raise HTTPException(401, "Invalid or expired API key.")

    # 2. Fetch the job
    conn = sqlite3.connect(get_db_path())
    try:
        row = conn.execute(
            "SELECT user_id, job_id, status, url, result_content, bytes_fetched, pii_removed, latency_ms, scrub_mode, error_msg FROM jobs WHERE job_id=?",
            (job_id,)).fetchone()
    finally:
        conn.close()

    if not row:
        raise HTTPException(404, "Job not found.")
    
    # 3. 🛡️ SECURITY FIX: Check Ownership (IDOR Protection)
    # row[0] is user_id
    if row[0] != user["id"]:
        # Do not reveal if job exists or not to other users
        raise HTTPException(404, "Job not found.")

    # 4. Return response
    resp = {"job_id": row[1], "status": row[2], "url": row[3]}
    if row[2] == "completed":
        resp.update({"content": row[4], "pii_redacted": row[6], "fetch_time_ms": row[7], "policy_decision": "ALLOWED"})
    elif row[2] in ("failed","blocked"):
        resp["error"] = row[9]
    return resp
