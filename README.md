# Safe Ingestion Engine v2

Security-first ingestion service with FastAPI, Celery, Redis-backed crawl budgets,
SSRF protection, PII scrubbing hooks, structured logging, rate limiting, tests,
Docker, and Kubernetes starter manifests.

## Highlights

- FastAPI API gateway
- Celery worker for async ingestion
- Redis-backed distributed crawl budget
- SQLite for local dev, swappable DB layer
- SSRF guard with private/reserved IP blocking
- robots.txt policy handling with configurable failure mode
- API-key auth with hashed keys
- Per-API-key + per-IP rate limiting hooks
- Structured JSON logging
- Security CI starter
- Docker Compose local stack
- Kubernetes starter manifests

## Quick start

```bash
cp .env.example .env
docker compose up --build
```

API docs:
- http://localhost:8000/docs

## Environment

Required:
- `PII_SALT` (>= 32 chars)
- `API_KEY_HASHES_JSON` (JSON array of sha256 hashes for API keys)
- `DASHBOARD_ADMIN_PASSWORD`

## Notes

This repo is a strong production-ready baseline, but you should still:
- switch SQLite to Postgres for heavier production load
- add secrets manager integration
- add observability backend (Prometheus / OpenTelemetry / Sentry)
- expand PII detection patterns for your target jurisdictions
