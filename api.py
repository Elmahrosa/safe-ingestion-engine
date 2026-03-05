from fastapi import FastAPI, BackgroundTasks, HTTPException, Header
import os
import uuid
from main import run_ingestion
from core.database import connect

app = FastAPI(title="Safe Ingestion API")

# Simple API Key check for SaaS monetisation
def verify_key(api_key: str):
    with connect() as conn:
        user = conn.execute("SELECT id FROM users WHERE api_key = ?", (api_key,)).fetchone()
        return user is not None

@app.post("/ingest")
async def trigger_ingest(url: str, background_tasks: BackgroundTasks, x_api_key: str = Header(None)):
    if not verify_key(x_api_key):
        raise HTTPException(status_code=403, detail="Invalid API Key")
    
    # Run the ingestion in the background so the API stays fast
    background_tasks.add_task(run_ingestion, url)
    
    return {"status": "accepted", "message": f"Ingestion started for {url}", "task_id": str(uuid.uuid4())}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
