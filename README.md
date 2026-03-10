<div align="center">

# 🛡 Safe Ingestion Engine

[![Python](https://img.shields.io/badge/Python-3.11-blue)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688)](https://fastapi.tiangolo.com)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ed)](https://docker.com)
[![Security](https://img.shields.io/badge/Security-Safe_by_Design-2ea043)](#security-model)
[![Trial](https://img.shields.io/badge/Trial-48h_Free-9b59ff)](https://safe.teosegypt.com)
[![Live](https://img.shields.io/badge/Live-safe.teosegypt.com-00d4aa)](https://safe.teosegypt.com)

**Compliance-first infrastructure for safe web data ingestion**

🌐 **Live:** https://safe.teosegypt.com &nbsp;·&nbsp; 📄 **Docs:** https://safe.teosegypt.com/docs.html
⏱ **5 free URLs — 48h trial — no card, no KYC, no auto-billing**
📬 **Contact:** aams1969 at gmail dot com

</div>

---

## Overview

Most scraping tools optimize for speed. **Safe Ingestion Engine optimizes for safety, governance, and auditability.**

```
URL → Policy Engine → Safe Fetch → PII Scrubber → Clean Content + Audit Log
```

Every ingestion request is evaluated for robots.txt compliance, YAML domain policy rules, SSRF safety, redirect chain safety, response size limits, and PII protection — before anything is stored.

---

## Architecture

```
FastAPI Gateway (api/server.py)
        │  X-API-Key validation · credit check via Google Sheet
        ▼
Celery Worker (api/tasks.py)
        │
        ├── PolicyEngine (core/policy.py)
        │     ├── robots.txt validation
        │     ├── YAML allow/deny rules
        │     └── per-domain crawl budgets
        │
        ├── SafeScraper (collectors/scraper.py)
        │     ├── SSRF protection
        │     ├── redirect-chain validation
        │     └── response size cap (5 MB)
        │
        └── PIIScrubber (core/pii.py)
              ├── email, phone, SSN, IPv4, credit card
              └── redact or HMAC-SHA256 hash mode
                       │
                       ▼
              SQLite (core/database.py)
              ├── raw_data
              ├── audit_log
              └── request_metrics
                       │
                       ▼
              Streamlit Dashboard (dashboard/app.py)
              └── audit evidence · metrics · CSV / PDF export

Google Apps Script (billing)
        ├── Trial signup → 5 credits emailed instantly
        ├── USDC payment → credits added automatically
        └── Credit check / deduct API for FastAPI middleware
```

**Stack:** Python 3.11 · FastAPI · Celery · Redis · SQLite · Streamlit · Docker · Google Apps Script

---

## Quick Start

### Hosted API

Sign up at https://safe.teosegypt.com — your API key arrives by email within seconds.

```bash
# 1. Submit an ingestion job
curl -X POST https://safe.teosegypt.com/v1/ingest_async \
  -H "X-API-Key: sk-safe-YOURKEYHERE" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "scrub_pii": true}'

# Returns: {"job_id": "abc123", "status": "queued", "credits_remaining": 9}

# 2. Poll for result
curl https://safe.teosegypt.com/v1/jobs/abc123 \
  -H "X-API-Key: sk-safe-YOURKEYHERE"

# Returns: {"status": "complete", "content": "...", "pii_redacted": 3}
```

### Self-Host with Docker

```bash
git clone https://github.com/Elmahrosa/safe-ingestion-engine.git
cd safe-ingestion-engine
cp .env.example .env
# Edit .env — set PII_SALT, DASHBOARD_ADMIN_PASSWORD, SHEET_WEBHOOK_URL, SHEET_API_SECRET
docker compose up -d
```

- API: http://localhost:8000/docs
- Dashboard: http://localhost:8501

---

## API Reference

All protected endpoints require the header:

```
X-API-Key: sk-safe-YOURKEYHERE
```

### `POST /v1/ingest_async`

Queue an ingestion job. Returns immediately with a job ID.

**Request body**
```json
{ "url": "https://example.com", "scrub_pii": true, "pii_mode": "redact" }
```

**Response**
```json
{ "job_id": "abc123", "status": "queued", "credits_remaining": 9 }
```

### `GET /v1/jobs/{job_id}`

Poll for job status and result. Poll every 1–2 seconds. Jobs retained 24 hours.

**Response**
```json
{
  "job_id": "abc123",
  "status": "complete",
  "url": "https://example.com",
  "content": "...clean scraped content...",
  "pii_redacted": 3,
  "policy_decision": "ALLOWED",
  "fetch_time_ms": 412
}
```

`status` values: `queued` · `running` · `complete` · `failed` · `blocked`
`policy_decision` values: `ALLOWED` · `BLOCKED_ROBOTS` · `BLOCKED_SSRF` · `BLOCKED_POLICY`

### `GET /health`

Health check — no auth required.

```json
{ "status": "ok", "workers": 2, "redis": "connected" }
```

### `GET /v1/me`

Returns account metadata for the authenticated API key.

```json
{
  "email": "user@example.com",
  "plan": "Monthly Growth",
  "credits": 847,
  "credits_used": 53,
  "status": "Active",
  "plan_expires": "2026-04-09"
}
```

---

## Configuration

Copy `.env.example` to `.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `PII_SALT` | *(required)* | HMAC salt for hash mode |
| `PII_MODE` | `redact` | `redact` or `hash` |
| `REDIS_URL` | `redis://redis:6379/0` | Celery broker |
| `DATA_DIR` | `data` | SQLite storage directory |
| `USER_AGENT` | `SafeSaaS/1.0` | Scraper user-agent string |
| `MAX_RESPONSE_BYTES` | `5242880` | Hard response size cap (5 MB) |
| `FETCH_TIMEOUT_SECONDS` | `10` | HTTP timeout |
| `MAX_REDIRECTS` | `5` | Maximum redirect hops |
| `DASHBOARD_ADMIN_PASSWORD` | *(blank = disabled)* | Protects admin dashboard tab |
| `CORS_ORIGINS` | *(blank)* | Comma-separated allowed origins |
| `SHEET_WEBHOOK_URL` | *(required)* | Google Apps Script `/exec` URL |
| `SHEET_API_SECRET` | *(required)* | Shared secret for Sheet ↔ API auth |

---

## Policy Rules

Edit `policies/policy.yml`:

```yaml
version: 1

defaults:
  max_requests_per_domain_per_day: 100
  min_seconds_between_requests: 2
  max_bytes: 5000000
  block_weekends: false

domains:
  - match: "*.gov"
    action: deny
    note: "Sensitive TLD — blocked by default"

  - match: "www.example.com"
    action: allow
    note: "Explicitly permitted"
```

---

## Credit System

Credits are managed via Google Sheets + Apps Script. No separate billing database required.

| Plan | Credits | Price | Validity |
|------|---------|-------|----------|
| Free Trial | **5 URLs** | $0 | 48 hours |
| Monthly Starter | 300 URLs | $29/mo | 30 days |
| Monthly Growth | 900 URLs | $79/mo | 30 days |
| Yearly Starter | 3,000 URLs | $290/yr | 365 days |
| Yearly Growth | 9,000 URLs | $790/yr | 365 days |

**Payment:** Send USDC on **Base network** to:
`0xd9CA11Dde3810a1BA9B5E1a4b6b76F5a419FAb41`

After sending, submit your transaction hash at https://safe.teosegypt.com/#pay — credits are added instantly and automatically.

> ⚠ Base network only. Do not send on Ethereum mainnet or BNB Chain.

---

## Security Model

| Control | Implementation |
|---------|----------------|
| SSRF blocking | Private, loopback, link-local, reserved, and cloud metadata IPs blocked |
| Redirect safety | Redirect chain revalidated hop-by-hop |
| robots.txt enforcement | Checked before every fetch; blocked requests don't cost credits |
| Policy rules | YAML-driven allow/deny and per-domain crawl budgets |
| Response limits | Stream aborted if max bytes exceeded |
| PII protection | Sensitive patterns scrubbed before storage |
| API key storage | SHA-256 hashed — never stored in plain text |
| Credit deduction | Atomic `UPDATE WHERE credits > 0` prevents race conditions |
| Container hardening | Non-root Docker user |

CI scanning: **Bandit · pip-audit · Trivy** — see `.github/workflows/ci.yml`

---

## Running Tests

```bash
pip install -r requirements.txt pytest pytest-asyncio httpx
pytest tests/ -v
```

---

## Changelog — v1.0.0

### Critical Fixes

| # | File | Bug | Fix |
|---|------|-----|-----|
| 1 | `core/database.py` | `log_audit`, `log_metrics`, `insert_raw` never defined | Added all three functions |
| 2 | `collectors/scraper.py` | `fetch_with_metrics()` called but never defined | Implemented method |
| 3 | `collectors/scraper.py` | Constructor `guard` arg mismatch → `TypeError` on startup | Removed unused param |
| 4 | `core/policy.py` | `policy.evaluate()` called but only `decide()` existed → `AttributeError` | Added `evaluate()` |
| 5 | `api.py` | API keys stored in plain text | SHA-256 hash before storage and lookup |
| 6 | `api/server.py` | TOCTOU race condition in credit deduction | Atomic `UPDATE … WHERE credits > 0` |

### Security Fixes

| # | File | Issue | Fix |
|---|------|-------|-----|
| 7 | `collectors/scraper.py` | No SSRF protection | Added `_validate_url()` guard |
| 8 | `collectors/scraper.py` | No response size cap | Streaming fetch with 5 MB hard limit |
| 9 | `core/compliance.py` | Bare `except:` silently blocked on any error | Fail-open with logged warning |
| 10 | `dashboard/app.py` | Admin panel exposed to anyone | Password-protected via env var |
| 11 | `.github/workflows/` | `actions/checkout@v6` doesn't exist | Pinned to `@v4`; added Trivy scan |

### Correctness & Quality

| # | File | Issue | Fix |
|---|------|-------|-----|
| 12 | `api/tasks.py` | DB connection never closed on success path | `try/finally conn.close()` |
| 13 | `core/pii.py` | PHONE regex matched any 8+ digit sequence | Tightened to NA format |
| 14 | `core/pii.py` | Missing SSN, IPv4, credit card patterns | Added all three |
| 15 | `core/policy.py` | No robots.txt integration | Integrated `_check_robots()` |
| 16 | `core/policy.py` | No crawl budget enforcement at runtime | In-memory per-domain counter with daily reset |
| 17 | `dashboard/app.py` | PDF export was blank page | ReportLab platypus export |
| 18 | `dashboard/app.py` | `request_metrics` table had no view | Added Metrics tab with KPI cards |
| 19 | `main.py` | `load_dotenv()` called on every import | Moved inside `if __name__ == "__main__"` |
| 20 | `docker-compose.yml` | No healthchecks — worker started before Redis | Added `healthcheck` + `condition: service_healthy` |

---

## CI/CD

GitHub Actions pipeline in `.github/workflows/ci.yml`:

- **Lint** — ruff + mypy on every push to `main` / `dev`
- **Security** — bandit + pip-audit + `.env` committed check
- **Tests** — pytest with Redis service, Python 3.11 + 3.12 matrix, 60% coverage threshold
- **Docker** — Trivy container scan (runs only after lint + tests pass)

---

## ⚠ .env Security

The `.env` file must **never** be committed to git. Rotate any secrets that may have been exposed.

```bash
echo ".env" >> .gitignore
git rm --cached .env
git commit -m "security: remove .env from tracking"
```

---

## Roadmap

- PostgreSQL production backend
- Webhook callbacks on job completion
- Signed audit export bundles
- Advanced per-plan policy controls
- Stripe payment integration

---

## Support

| Platform | Link |
|----------|------|
| ☕ Ko-fi | [ko-fi.com/elmahrosa](https://ko-fi.com/elmahrosa) |
| ❤️ GitHub Sponsors | [github.com/sponsors/Elmahrosa](https://github.com/sponsors/Elmahrosa) |
| 🍵 Buy Me a Coffee | [buymeacoffee.com/elmahrosa](https://buymeacoffee.com/elmahrosa) |
| 💼 Consulting | aams1969 at gmail dot com |

---

## License

**Proprietary** — see [LICENSE](LICENSE) for full terms.

---

<div align="center">

**Built by Ayman Seif · Elmahrosa International 🇪🇬**

[⏱ Start Free Trial](https://safe.teosegypt.com) &nbsp;·&nbsp; [☕ Ko-fi](https://ko-fi.com/elmahrosa) &nbsp;·&nbsp; [❤️ GitHub Sponsors](https://github.com/sponsors/Elmahrosa)

</div>
