# Safe Ingestion Engine — Hardened Final Repo

This package is a hardened rebuild of the public `safe-ingestion-engine` structure focused on launch readiness.

## Included hardening
- API keys removed from Celery payloads
- Salted HMAC API-key hashing
- Async DNS SSRF validation
- ReDoS-safe credit-card regex
- Fail-secure robots.txt fallback
- SQLite production warning + retry helper
- Structured security logging
- HTTP circuit breaker
- Idempotency keys for submission
- Streaming response-size validation
- Prometheus `/metrics`
- CI with Bandit + pip-audit
- Security regression workflow
- Rotation script and launch docs

## Quick start
1. Copy `.env.example` to `.env`
2. Fill salts and Redis/database settings
3. Run `docker compose up --build`
4. Open `http://localhost:8000/health`

## Test
```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```
