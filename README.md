<div align="center">

<br/>

<img src="https://raw.githubusercontent.com/Elmahrosa/safe-ingestion-engine/main/logo.png" width="100" alt="Safe Ingestion Engine"/>

<br/><br/>

# Safe Ingestion Engine

**Compliance-first infrastructure for ethical web data ingestion**

[![Python 3.11](https://img.shields.io/badge/Python-3.11-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=flat-square&logo=docker&logoColor=white)](https://docker.com)
[![Security](https://img.shields.io/badge/Security-Safe_by_Design-2ea043?style=flat-square&logo=shield&logoColor=white)](#security-model)
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
FastAPI Gateway  ──  api/server.py
    │   X-API-Key auth · credit check · CORS
    ▼
Celery Worker  ──  api/tasks.py
    │
    ├── PolicyEngine  ──  core/policy.py
    │       ├── robots.txt validation (per-domain, cached)
    │       ├── YAML allow/deny rules
    │       └── per-domain crawl budget (in-memory, daily reset)
    │
    ├── SafeScraper  ──  collectors/scraper.py
    │       ├── SSRF guard (blocks private, loopback, cloud metadata IPs)
    │       ├── redirect-chain revalidation (hop-by-hop)
    │       ├── response size cap (hard 5 MB abort)
    │       └── configurable timeout + user-agent
    │
    └── PIIScrubber  ──  core/pii.py
            ├── email, phone (NA format), SSN, IPv4, credit card
            └── redact mode OR HMAC-SHA256 hash mode
                    │
                    ▼
            SQLite  ──  core/database.py
            ├── raw_data
            ├── audit_log
            └── request_metrics
                    │
                    ▼
            Streamlit Dashboard  ──  dashboard/app.py
            ├── Audit log viewer + CSV/PDF export
            ├── Metrics tab with KPI cards
            └── Admin panel (password-protected)

Google Apps Script  ──  billing backend
    ├── Trial signup → API key generated instantly and shown on screen
    ├── USDC payment → credits added automatically on-chain verification
    └── Credit check / deduct middleware for FastAPI
```

**Stack:** Python 3.11 · FastAPI · Celery · Redis · SQLite · Streamlit · Docker Compose · Google Apps Script

---

## Quick Start

### Hosted API (Recommended)

1. Go to **[safe.teosegypt.com](https://safe.teosegypt.com)**
2. Sign up — your API key appears on screen instantly and is also emailed to you
3. Start ingesting:

```bash
# Submit an ingestion job
curl -X POST https://safe.teosegypt.com/v1/ingest_async \
  -H "X-API-Key: sk-safe-YOURKEYHERE" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "scrub_pii": true}'

# Returns
# {"job_id": "abc123", "status": "queued", "credits_remaining": 4}

# Poll for result (every 1–2 seconds)
curl https://safe.teosegypt.com/v1/jobs/abc123 \
  -H "X-API-Key: sk-safe-YOURKEYHERE"

# Returns
# {"status": "complete", "content": "...", "pii_redacted": 2, "fetch_time_ms": 391}
```

### Self-Host with Docker

```bash
git clone https://github.com/Elmahrosa/safe-ingestion-engine.git
cd safe-ingestion-engine

cp .env.example .env
# Edit .env — minimum required: PII_SALT, DASHBOARD_ADMIN_PASSWORD,
#             SHEET_WEBHOOK_URL, SHEET_API_SECRET

docker compose up -d
```

| Service | URL |
|---------|-----|
| API + Swagger | http://localhost:8000/docs |
| Streamlit Dashboard | http://localhost:8501 |

---

## API Reference

All protected endpoints require:

```
X-API-Key: sk-safe-YOURKEYHERE
```

### `POST /v1/ingest_async`

Queue an ingestion job. Returns a job ID in under 100 ms.

```json
// Request
{ "url": "https://example.com", "scrub_pii": true, "pii_mode": "redact" }

// Response
{ "job_id": "abc123", "status": "queued", "credits_remaining": 4 }
```

### `GET /v1/jobs/{job_id}`

Poll for result. Jobs retained for 24 hours.

```json
{
  "job_id": "abc123",
  "status": "complete",
  "url": "https://example.com",
  "content": "...clean content...",
  "pii_redacted": 2,
  "policy_decision": "ALLOWED",
  "fetch_time_ms": 391
}
```

| `status` | Meaning |
|----------|---------|
| `queued` | Waiting for a worker |
| `running` | Fetch in progress |
| `complete` | Done — content available |
| `failed` | Fetch or processing error |
| `blocked` | Stopped by policy/robots — no credit deducted |

| `policy_decision` | Reason |
|-------------------|--------|
| `ALLOWED` | All checks passed |
| `BLOCKED_ROBOTS` | robots.txt disallows |
| `BLOCKED_SSRF` | Private/reserved IP detected |
| `BLOCKED_POLICY` | YAML domain rule matched |

### `GET /v1/me`

Returns account info for the authenticated key.

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

### `GET /health`

Health check — no auth required.

```json
{ "status": "ok", "workers": 2, "redis": "connected" }
```

---

## Configuration

Copy `.env.example` to `.env` before running:

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `PII_SALT` | — | ✅ | HMAC salt for hash mode |
| `PII_MODE` | `redact` | — | `redact` or `hash` |
| `REDIS_URL` | `redis://redis:6379/0` | — | Celery broker URL |
| `DATA_DIR` | `data` | — | SQLite storage directory |
| `USER_AGENT` | `SafeSaaS/1.0` | — | HTTP User-Agent string |
| `MAX_RESPONSE_BYTES` | `5242880` | — | Hard response size cap (5 MB) |
| `FETCH_TIMEOUT_SECONDS` | `10` | — | HTTP request timeout |
| `MAX_REDIRECTS` | `5` | — | Maximum redirect hops |
| `DASHBOARD_ADMIN_PASSWORD` | — | — | Protects admin dashboard tab |
| `CORS_ORIGINS` | — | — | Comma-separated allowed origins |
| `SHEET_WEBHOOK_URL` | — | ✅ | Google Apps Script `/exec` URL |
| `SHEET_API_SECRET` | — | ✅ | Shared secret for Sheet ↔ API auth |

> ⚠ Never commit `.env` to git. Run `git rm --cached .env` if it was ever tracked.

---

## Policy Rules

Edit `policies/policy.yml` to control per-domain scraping behaviour:

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
    max_requests_per_domain_per_day: 500
    note: "Trusted partner domain"
```

The `PolicyEngine` evaluates rules in order. First match wins. `robots.txt` is always checked regardless of YAML rules.

---

## Credit System

Credits are managed via Google Sheets + Apps Script — no separate billing database required.

| Plan | Credits | Price | Validity |
|------|---------|-------|----------|
| Free Trial | **5 URLs** | $0 | 48 hours |
| Monthly Starter | 300 URLs | $29 / mo | 30 days |
| Monthly Growth | 900 URLs | $79 / mo | 30 days |
| Yearly Starter | 3,000 URLs | $290 / yr | 365 days |
| Yearly Growth | 9,000 URLs | $790 / yr | 365 days |

**Payment:** Send exact USDC on **Base network** to:

```
0xd9CA11Dde3810a1BA9B5E1a4b6b76F5a419FAb41
```

Then submit your transaction hash at **[safe.teosegypt.com/#pay](https://safe.teosegypt.com/#pay)** — credits are added automatically.

> ⚠ **Base network only.** Do not send on Ethereum mainnet or BNB Chain.

---

## Security Model

| Layer | Control | Implementation |
|-------|---------|----------------|
| Network | SSRF blocking | Private, loopback, link-local, reserved, and cloud metadata IPs blocked at `_validate_url()` |
| Network | Redirect safety | Redirect chain revalidated hop-by-hop — no open redirect exploitation |
| Compliance | robots.txt | Checked before every fetch via `_check_robots()`; blocked requests cost zero credits |
| Compliance | Policy rules | YAML-driven allow/deny with per-domain crawl budgets and daily reset |
| Fetch | Response limits | Streaming fetch aborted the moment `MAX_RESPONSE_BYTES` is exceeded |
| Data | PII protection | Email, phone, SSN, IPv4, credit card scrubbed before any storage |
| Auth | API key storage | SHA-256 hashed — never stored or compared in plain text |
| Billing | Credit deduction | Atomic `UPDATE … WHERE credits > 0` prevents TOCTOU race conditions |
| Runtime | Container | Non-root Docker user; Trivy image scan in CI |

CI scanning pipeline: **Bandit · pip-audit · Trivy** — see `.github/workflows/ci.yml`

---

## Running Tests

```bash
pip install -r requirements.txt pytest pytest-asyncio httpx
pytest tests/ -v
```

Coverage threshold: **60%** (enforced in CI). Redis required for integration tests — it is started automatically by the GitHub Actions service container.

---

## CI/CD Pipeline

Defined in `.github/workflows/ci.yml`:

| Stage | Tools | Trigger |
|-------|-------|---------|
| Lint | ruff, mypy | Push to `main` or `dev` |
| Security scan | bandit, pip-audit, `.env` committed check | Push to `main` or `dev` |
| Tests | pytest, Python 3.11 + 3.12 matrix | Push to `main` or `dev` |
| Container scan | Trivy | After lint + tests pass |

---

## Changelog — v1.0.0

### Critical Bug Fixes

| # | File | Bug | Fix |
|---|------|-----|-----|
| 1 | `core/database.py` | `log_audit`, `log_metrics`, `insert_raw` called everywhere but never defined | Implemented all three |
| 2 | `collectors/scraper.py` | `fetch_with_metrics()` called in tasks but never defined | Implemented method |
| 3 | `collectors/scraper.py` | Constructor `guard` arg mismatch → `TypeError` on every startup | Removed unused param |
| 4 | `core/policy.py` | `policy.evaluate()` called by main + tasks; only `decide()` existed → `AttributeError` | Added `evaluate()` as canonical entry point |
| 5 | `api.py` | API keys stored and compared in plain text | SHA-256 hash before storage and lookup |
| 6 | `api/server.py` | TOCTOU race in credit check — two concurrent requests could both pass | Atomic `UPDATE … WHERE credits > 0` + rowcount check |

### Security Fixes

| # | File | Issue | Fix |
|---|------|-------|-----|
| 7 | `collectors/scraper.py` | No URL validation → SSRF against localhost, 192.168.x.x possible | Added `_validate_url()` SSRF guard |
| 8 | `collectors/scraper.py` | No response size cap → large responses could exhaust worker memory | Streaming fetch with 5 MB hard abort |
| 9 | `core/compliance.py` | Bare `except:` silently returned BLOCKED on timeouts and unrelated errors | Fail-open with logged warning |
| 10 | `dashboard/app.py` | Admin section exposed to all users | Password-protected via `DASHBOARD_ADMIN_PASSWORD` env var |
| 11 | `.github/workflows/` | `actions/checkout@v6` and `setup-python@v6` do not exist | Pinned to `@v4` / `@v5`; added Trivy container scan |

### Correctness & Quality

| # | File | Issue | Fix |
|---|------|-------|-----|
| 12 | `api/tasks.py` | DB connection opened but never closed on success path | `try/finally conn.close()` |
| 13 | `core/pii.py` | PHONE regex matched any 8+ digit sequence | Tightened to recognisable NA phone format |
| 14 | `core/pii.py` | SSN, IPv4, credit card patterns missing | Added all three |
| 15 | `core/policy.py` | No robots.txt integration despite being primary policy entry point | Integrated `_check_robots()` |
| 16 | `core/policy.py` | No crawl-budget enforcement at runtime | In-memory per-domain counter with daily reset |
| 17 | `dashboard/app.py` | PDF export produced blank page | ReportLab platypus export with actual audit table |
| 18 | `dashboard/app.py` | `request_metrics` table had no dashboard view | Added Metrics tab with KPI cards |
| 19 | `main.py` | `load_dotenv()` called on every import, overriding Docker env vars | Moved inside `if __name__ == "__main__"` guard |
| 20 | `docker-compose.yml` | No healthchecks — worker started before Redis was ready | Added `healthcheck` + `condition: service_healthy` |

---

## Roadmap

- [ ] PostgreSQL production backend (replace SQLite for multi-worker deployments)
- [ ] Webhook callbacks on job completion
- [ ] Signed, tamper-evident audit export bundles
- [ ] Advanced per-plan policy controls
- [ ] Stripe card payment integration
- [ ] Webhook signature verification for Apps Script events

---

## Support

If this project saves you time, consider supporting it:

| Platform | Link |
|----------|------|
| ☕ Ko-fi | [ko-fi.com/elmahrosa](https://ko-fi.com/elmahrosa) |
| ❤️ GitHub Sponsors | [github.com/sponsors/Elmahrosa](https://github.com/sponsors/Elmahrosa) |
| 🍵 Buy Me a Coffee | [buymeacoffee.com/elmahrosa](https://buymeacoffee.com/elmahrosa) |
| 💼 Consulting & Enterprise | aams1969 at gmail dot com |

---

## License

**Proprietary** — see [LICENSE](LICENSE) for full terms. Commercial use requires a paid plan.

---

<div align="center">

**Built by [Ayman Seif](https://www.linkedin.com/in/aymanseif/) · Elmahrosa International 🇪🇬**

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Ayman_Seif-0A66C2?style=flat-square&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/aymanseif/)
[![Ko-fi](https://img.shields.io/badge/Ko--fi-Support-FF5E5B?style=flat-square&logo=ko-fi&logoColor=white)](https://ko-fi.com/elmahrosa)
[![GitHub Sponsors](https://img.shields.io/badge/Sponsors-❤️-EA4AAA?style=flat-square&logo=githubsponsors&logoColor=white)](https://github.com/sponsors/Elmahrosa)

[⚡ Start Free Trial](https://safe.teosegypt.com) &nbsp;·&nbsp; [📄 Read the Docs](https://safe.teosegypt.com/docs.html) &nbsp;·&nbsp; [👤 My Account](https://safe.teosegypt.com/portal.html)

</div>
