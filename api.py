from fastapi import FastAPI, BackgroundTasks, HTTPException, Header
import uuid
from main import run_ingestion
from core.database import connect

app = FastAPI(title="Safe Ingestion API")

def verify_and_deduct_credit(api_key: str):
    """Checks if key exists and user has enough credits, then deducts one."""
    with connect() as conn:
        # Check if user exists and has at least 1 credit
        user = conn.execute(
            "SELECT id, credits FROM users WHERE api_key = ?", (api_key,)
        ).fetchone()
        
        if not user:
            return False, "Invalid API Key"
        
        user_id, credits = user
        if credits <= 0:
            return False, "Insufficient credits. Please top up your account."
        
        # Deduct 1 credit for the new request
        conn.execute(
            "UPDATE users SET credits = credits - 1 WHERE api_key = ?", (api_key,)
        )
        conn.commit()
        return True, "Success"

@app.post("/ingest")
async def trigger_ingest(url: str, background_tasks: BackgroundTasks, x_api_key: str = Header(None)):
    if not x_api_key:
        raise HTTPException(status_code=401, detail="API Key missing")

    # Verify and deduct credit before starting the task
    success, message = verify_and_deduct_credit(x_api_key)
    
    if not success:
        # 402 is the standard code for 'Payment Required'
        raise HTTPException(status_code=402, detail=message)
    
    # Run the ingestion in the background so the API stays fast
    task_id = str(uuid.uuid4())
    background_tasks.add_task(run_ingestion, url)
    
    return {
        "status": "accepted", 
        "message": f"Ingestion started for {url}", 
        "task_id": task_id
    }

if __name__ == "__main__":
    import uvicorn
    # Start the server
    uvicorn.run(app, host="0.0.0.0", port=8000)
