from fastapi import Header, HTTPException, Request

from core.auth import is_valid_api_key
from core.config import get_settings

settings = get_settings()

async def require_api_key(x_api_key: str = Header(...)):
    if not is_valid_api_key(x_api_key):
        raise HTTPException(status_code=401, detail="invalid api key")
    return x_api_key

def rate_limit_key(request: Request) -> str:
    api_key = request.headers.get("x-api-key")
    if api_key:
        return f"api:{api_key}"
    client = request.client.host if request.client else "unknown"
    return f"ip:{client}"
