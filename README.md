# Safe Ingestion Engine — Hardened Final Repo v2.1

This package is the final cleaned repo bundle for `safe-ingestion-engine`, updated after a full code review of the rebuilt codebase.

## What was already correct
The repo already had the major hardening work in place:
- HMAC API key hashing
- SSRF guard
- circuit breaker
- Prometheus metrics
- idempotency keys
- structured logging
- PII scrubbing
- Redis queue + Celery worker

## Final production gaps closed in this bundle
1. **Billing bridge fixed** — API keys now live in Redis, so Google Apps Script issued keys are visible to the API without storing hashes in `.env`.
2. **Async job polling added** — `GET /v1/jobs/{job_id}` now exists for the documented async flow.
3. **Healthchecks added** — `docker-compose.yml` now waits for Redis and API readiness.
4. **`.env.example` corrected** — includes `GAS_WEBHOOK_SECRET` and marks `API_KEY_HASHES_JSON` as legacy.

## Billing architecture
The intended production billing flow is now:

```text
User payment
   ↓
Google Apps Script
   ↓
POST /internal/register-key
   ↓
Redis key registry
   ↓
FastAPI request validation + credit deduction
```

Keys are validated against Redis and credits are deducted atomically with Redis transactions.

## Included files
- updated `core/auth.py`
- updated `api/routes/ingest.py`
- updated `core/config.py`
- updated `docker-compose.yml`
- updated `.env.example`
- updated `scripts/smoke_test.sh`
- added `scripts/gas_billing_bridge.js`
- cleaned out `__pycache__` and `.pyc` files
- added `.gitignore`

## Quick start
1. Copy `.env.example` to `.env`
2. Generate and paste fresh values for:
   - `PII_SALT`
   - `API_KEY_SALT`
   - `GAS_WEBHOOK_SECRET`
3. Start Redis + API + worker
4. Register a key through the internal webhook
5. Submit a job to `/v1/ingest_async`
6. Poll `/v1/jobs/{job_id}`

Generate secrets with:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

## Smoke test

```bash
GAS_WEBHOOK_SECRET=your_secret_here bash scripts/smoke_test.sh
```

## Notes
- `API_KEY_HASHES_JSON` remains for legacy fallback only.
- Do not commit a real `.env`.
- For Windows Git Bash, use `cp`, not `copy`.
