from contextlib import asynccontextmanager
from fastapi import FastAPI
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.responses import JSONResponse

from api.routes.health import router as health_router
from api.routes.ingest import router as ingest_router
from api.routes.jobs import router as jobs_router
from core.config import get_settings
from core.database import init_db
from core.logging import configure_logging
from security.rate_limit import limiter

settings = get_settings()
configure_logging(settings.log_level)

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(title=settings.app_name, version="2.0.0", lifespan=lifespan)
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

@app.exception_handler(RateLimitExceeded)
async def ratelimit_handler(request, exc):
    return JSONResponse(status_code=429, content={"detail": "rate limit exceeded"})

app.include_router(health_router, tags=["health"])
app.include_router(ingest_router, prefix="/v1", tags=["ingest"])
app.include_router(jobs_router, prefix="/v1", tags=["jobs"])
