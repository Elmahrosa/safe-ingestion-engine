<div align="center">

<br/>

<img src="https://raw.githubusercontent.com/Elmahrosa/safe-ingestion-engine/main/logo.png" width="100" alt="Safe Ingestion Engine"/>

<br/><br/>

# Safe Ingestion Engine

**Compliance-first infrastructure for ethical web data ingestion**

[![Python 3.11](https://img.shields.io/badge/Python-3.11-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=flat-square&logo=docker&logoColor=white)](https://docker.com)
[![Redis](https://img.shields.io/badge/Redis-7-DC382D?style=flat-square&logo=redis&logoColor=white)](https://redis.io)
[![License](https://img.shields.io/badge/License-Proprietary-orange?style=flat-square)](LICENSE)
[![Live](https://img.shields.io/badge/Live-safe.teosegypt.com-00d4aa?style=flat-square)](https://safe.teosegypt.com)

<br/>

🌐 **[safe.teosegypt.com](https://safe.teosegypt.com)** &nbsp;·&nbsp; 📄 **[Docs](https://safe.teosegypt.com/docs.html)** &nbsp;·&nbsp; 👤 **[My Account](https://safe.teosegypt.com/portal.html)** &nbsp;·&nbsp; 💼 **[LinkedIn](https://www.linkedin.com/in/aymanseif/)**

⚡ **5 free URLs · 48-hour trial · no card · no KYC · no auto-billing**

</div>

---

## Why Safe Ingestion Engine?

Most scraping tools are built for speed. **Safe Ingestion Engine is built for safety, governance, and auditability.**

Every request is evaluated through a multi-layer pipeline before a single byte is fetched:

```
URL Input
    │
    ▼
Policy Engine ── robots.txt · YAML rules · crawl budget · SSRF guard
    │
    ▼
Safe Fetch ──── rate-limited · redirect-safe · size-capped (5 MB)
    │
    ▼
PII Scrubber ── email · phone · SSN · IPv4 · credit card
    │
    ▼
Clean Content + Full Audit Log
```

Blocked requests cost **zero** credits. Every outcome is logged.

---

## Architecture

```
FastAPI Gateway  ──  api/server.py            ← single entrypoint
    │   X-API-Key auth · Redis key lookup · CORS
    │
    ├── POST  /v1/ingest          submit URL, returns job_id
    ├── GET   /v1/jobs/{job_id}   poll job status / result
    ├── GET   /health             liveness check
    ├── GET   /metrics            Prometheus-format metrics
    ├── GET   /v1/status          JSON health + counters
    └── POST  /internal/register-key   (GAS billing bridge, hidden from docs)

Celery Worker  ──  workers/tasks.py
    │   async URL fetch · PII scrub · audit log
    │
    └── Redis  (broker + job state + API key store)

Billing Bridge  ──  Google Apps Script
    │   payment confirmed → POST /internal/register-key
    │   key stored in Redis with TTL
    └── email sent to customer with API key
```

**API keys are never passed in Celery payloads.** The key is validated at the gateway; only the `job_id` travels to the worker.

---

## API Reference

### Authentication

All endpoints (except `/health`, `/metrics`, `/v1/status`) require:

```
X-API-Key: sk-safe-XXXXXXXXXX
```

### Submit a URL

```
POST /v1/ingest
Content-Type: application/json
X-API-Key: sk-safe-XXXXXXXXXX
```

```json
{
  "url": "https://example.com/article",
  "scrub_pii": true,
  "webhook_url": "https://your-server.com/callback"
}
```

Response `200 OK`:
```json
{
  "job_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "status": "queued",
  "submitted_at": "2025-01-01T00:00:00+00:00"
}
```

### Poll Job Status

```
GET /v1/jobs/{job_id}
X-API-Key: sk-safe-XXXXXXXXXX
```

Response:
```json
{
  "job_id": "3fa85f64-...",
  "status": "done",
  "result": {
    "text": "Cleaned content with PII removed...",
    "metadata": { "title": "...", "content_type": "text/html" }
  },
  "created_at": "2025-01-01T00:00:00+00:00",
  "updated_at": "2025-01-01T00:00:05+00:00"
}
```

Status values: `queued` → `processing` → `done` | `failed`

### Health & Metrics

| Endpoint | Auth | Response |
|---|---|---|
| `GET /health` | None | `{"status":"ok","version":"1.0.0"}` |
| `GET /metrics` | None | Prometheus plaintext |
| `GET /v1/status` | None | JSON counters + Redis status |
| `GET /docs` | None | Swagger UI |

---

## Pricing

| Plan | Credits | Period | Price |
|---|---|---|---|
| Trial | 5 | 48 hours | Free |
| Starter | 300 | 30 days | $29 USDC |
| Growth | 900 | 30 days | $79 USDC |
| Yearly Starter | 3,000 | 365 days | $290 USDC |
| Yearly Growth | 9,000 | 365 days | $790 USDC |

Payment: USDC on Base network · wallet `0xd9CA11Dde3810a1BA9B5E1a4b6b76F5a419FAb41`

---

## Local Development

### Prerequisites

- Python 3.11+
- Redis 7+ running locally
- Docker (optional)

### Setup

```bash
# 1. Clone
git clone https://github.com/Elmahrosa/safe-ingestion-engine.git
cd safe-ingestion-engine

# 2. Virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env — set PII_SALT, API_KEY_SALT, GAS_WEBHOOK_SECRET, REDIS_URL

# 5. Run
python -m uvicorn api.server:app --host 0.0.0.0 --port 8000 --reload
```

Open:
- `http://127.0.0.1:8000/health`
- `http://127.0.0.1:8000/docs`

### Docker Compose

```bash
cp .env.example .env   # fill in values first
docker compose up -d
docker compose logs -f api
```

Services started: `redis` → `api` → `worker` (each waits for the previous to be healthy).

### Register a Test API Key

```bash
# With USE_REDIS_AUTH=true, register a key manually for testing:
python - <<'EOF'
from core.auth import register_key
register_key("sk-safe-TESTKEY000", ttl=86400)
print("Registered")
EOF
```

### Smoke Test

```bash
./scripts/smoke_test.sh               # localhost:8000
./scripts/smoke_test.sh https://safe.teosegypt.com
```

### Security Checks

```bash
pytest
bandit -r .
pip-audit
```

---

## Security Model

- **API keys** are salted SHA-256 hashed before storage — raw keys never touch Redis or logs
- **API keys are not included in Celery payloads** — validated at the gateway only
- **PII scrubbing** runs on every response when `scrub_pii: true` (default)
- **SSRF protection** — internal IPs and reserved ranges are blocked before fetch
- **Billing bridge** uses a shared secret (`GAS_WEBHOOK_SECRET`) verified server-side
- **`.env` is gitignored** — secrets never committed

---

## Repository Structure

```
safe-ingestion-engine/
├── api/
│   ├── server.py              ← single app entrypoint (api.server:app)
│   └── routes/
│       ├── ingest.py          ← POST /v1/ingest, GET /v1/jobs/{job_id}
│       └── metrics.py         ← GET /metrics, GET /v1/status
├── core/
│   └── auth.py                ← Redis-backed API key auth
├── connectors/
│   └── base.py                ← BaseConnector + HttpConnector
├── scripts/
│   ├── rotate_api_keys.py     ← key rotation / revocation tool
│   └── smoke_test.sh          ← end-to-end smoke test
├── docs/
│   ├── PRODUCTION_CHECKLIST.md
│   └── AI_AGENT_INTEGRATION.md
├── .env.example
├── .gitignore
├── VERSION
├── docker-compose.yml
└── README.md
```

---

## Changelog

### v1.0.0
- Single entrypoint: `api.server:app`
- Redis-backed API key auth (single consistent model — no split static/Redis path)
- `POST /v1/ingest` + `GET /v1/jobs/{job_id}` polling endpoint
- `GET /metrics` Prometheus endpoint
- `GET /v1/status` JSON health endpoint
- GAS billing bridge via `/internal/register-key` (hidden from public docs)
- API keys not included in Celery payloads
- `connectors/base.py` — `BaseConnector` + `HttpConnector`
- `scripts/rotate_api_keys.py` — key rotation / revocation
- `scripts/smoke_test.sh` — automated smoke tests
- `docs/PRODUCTION_CHECKLIST.md`
- `docs/AI_AGENT_INTEGRATION.md` — LangChain + LlamaIndex examples
- Docker Compose with Redis/API/worker healthchecks and startup ordering

---

## Author

**Ayman Seif** · [LinkedIn](https://www.linkedin.com/in/aymanseif/) · aams1969@gmail.com  
Elmahrosa International

> *"Safety is not a feature. It is the foundation."*
