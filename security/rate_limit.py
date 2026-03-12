from slowapi import Limiter
from fastapi import Request


def rate_limit_key(request: Request) -> str:
    api_key = request.headers.get("x-api-key")
    if api_key:
        return f"api:{api_key}"
    client = request.client.host if request.client else "unknown"
    return f"ip:{client}"


limiter = Limiter(key_func=rate_limit_key)
