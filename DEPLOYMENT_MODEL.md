# Architecture

## Flow

1. FastAPI receives request
2. API key is validated
3. Celery task is queued
4. Worker applies robots and crawl-budget policy
5. Worker fetches content through SSRF-safe connector
6. PII scrubbing runs before persistence
7. Result excerpt and status are stored through SQLAlchemy

## Main modules

- `api/` HTTP entrypoints
- `collectors/` source fetchers
- `core/` config, auth, models, logging, policy, PII
- `services/` business orchestration
- `infrastructure/queue/` Celery app and worker task
- `security/` rate limiting
- `tests/` regression coverage
