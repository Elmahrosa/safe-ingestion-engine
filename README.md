<div align="center">

<img src="https://raw.githubusercontent.com/Elmahrosa/safe-ingestion-engine/main/logo.png" width="110"/>

# 🛡️ Safe Ingestion Engine

### Compliance-First Web Data Ingestion API

robots.txt enforced · PII scrubbed · SSRF blocked · full audit log · async by default

[![Python](https://img.shields.io/badge/Python-3.11-blue?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=flat-square&logo=docker&logoColor=white)](https://docker.com)
[![Security](https://img.shields.io/badge/Security-Safe_by_Design-green?style=flat-square)](#security)
[![License](https://img.shields.io/badge/License-Commercial-orange?style=flat-square)](./LICENSE)
[![CI](https://github.com/Elmahrosa/safe-ingestion-engine/actions/workflows/security.yml/badge.svg)](https://github.com/Elmahrosa/safe-ingestion-engine/actions)

**🌐 Hosted API →** https://safe.teosegypt.com  
**⚡ Free Trial →** https://safe.teosegypt.com/#trial  
**📖 Docs →** https://safe.teosegypt.com/docs.html  
**💬 Issues →** https://github.com/Elmahrosa/safe-ingestion-engine/issues

</div>

---

## Why Safe Ingestion Engine?

Most scraping tools optimize for throughput. Safe Ingestion Engine optimizes for **legal defensibility**.

When your compliance team asks *"was this scrape ethical and auditable?"* — you need an answer. Safe Ingestion Engine makes compliance the default, not the afterthought.

| Concern | Typical Scraper | Safe Ingestion Engine |
|---|---|---|
| robots.txt | Optional / ignored | **Enforced before every fetch** |
| PII in data | Passes through | **Auto-redacted (email, phone, SSN, CC, IP)** |
| SSRF attacks | Unprotected | **Blocked at network layer** |
| Audit trail | None | **Full log, PDF-exportable** |
| Rate limiting | None | **Per-domain crawl budgets via YAML** |
| Compliance posture | Unknown | **GDPR-friendly by architecture** |
| AI agent safety | None | **Drop-in compliant layer for autonomous agents** |

---

## How It Works

Every request passes through a controlled safety pipeline before any network call is made.

```
URL Input
    │
    ▼
Policy Engine ──── robots.txt check
    │           ── YAML domain rules
    │           ── crawl budget enforcement
    │           ── SSRF validation
    │
    ▼
Safe Fetch ──────── redirect chain validated hop-by-hop
    │           ── response size capped (5 MB)
    │           ── timeout enforced (10s default)
    │
    ▼
PII Scrubber ────── email · phone · SSN · IPv4 · credit card
    │           ── scrubbed IN MEMORY before any write
    │
    ▼
Clean Content + Audit Log
```

**Blocked requests are not billed** and remain visible in your audit log.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   Client / AI Agent                          │
└──────────────────────────┬──────────────────────────────────┘
                           │  POST /v1/ingest_async
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              FastAPI  (api/server.py)                        │
│   Auth · Rate Limit · Credit Deduction (atomic SQL)         │
└──────────────────────────┬──────────────────────────────────┘
                           │  Celery task enqueue
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              Celery Worker  (api/tasks.py)                   │
│                                                             │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ PolicyEngine│  │  SafeScraper │  │   PIIScrubber    │  │
│  │ robots.txt  │  │  SSRF guard  │  │  email / phone / │  │
│  │ YAML rules  │  │  size cap    │  │  SSN / IP / CC   │  │
│  │ crawl budget│  │  timeout     │  │  redact or hash  │  │
│  └─────────────┘  └──────────────┘  └──────────────────┘  │
└──────────────────────────┬──────────────────────────────────┘
                           │
              ┌────────────┴────────────┐
              ▼                         ▼
       Redis (broker)           SQLite / PostgreSQL
       Celery results           Audit log · metrics
                                         │
                                         ▼
                               Streamlit Dashboard
                               Metrics · Audit export · Admin
```

**Stack:** Python 3.11 · FastAPI · Celery · Redis · SQLite · Streamlit · Docker

---

## Quick Start (Self-Hosted)

### Prerequisites

- Docker Desktop (or Docker + Compose)
- Git

### Up in 3 Commands

```bash
git clone https://github.com/Elmahrosa/safe-ingestion-engine.git
cd safe-ingestion-engine
cp .env.example .env        # set PII_SALT and DASHBOARD_ADMIN_PASSWORD at minimum
docker compose up --build
```

| Service | URL |
|---|---|
| API (Swagger UI) | http://localhost:8000/docs |
| Dashboard | http://localhost:8501 |

### First API Call

```bash
export KEY="sk-safe-YOURKEYHERE"

# 1. Submit a URL
curl -X POST http://localhost:8000/v1/ingest_async \
  -H "X-API-Key: $KEY" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "scrub_pii": true}'
# → {"job_id": "abc123", "status": "queued"}

# 2. Poll for result
curl http://localhost:8000/v1/jobs/abc123 \
  -H "X-API-Key: $KEY"
# → {"status": "complete", "content": "...", "pii_redacted": 3}
```

---

## Hosted API

A fully managed version runs at **https://safe.teosegypt.com**

- Managed workers and Redis — zero setup
- Policy-enforced ingestion
- Full audit logging and PDF export
- Instant API key delivery by email
- Pay per URL — no subscription required

**Get 5 free URL credits → https://safe.teosegypt.com/#trial**  
No credit card required.

---

## API Reference

### `POST /v1/ingest_async`

Submit a URL for compliant ingestion.

| Field | Type | Required | Description |
|---|---|---|---|
| `url` | string | ✅ | Target URL to fetch |
| `scrub_pii` | boolean | ❌ | Default `true`. Set `false` to disable PII scrubbing |
| `policy_override` | object | ❌ | Override YAML policy fields per-request |

**Request**
```json
{
  "url": "https://example.com/public/data",
  "scrub_pii": true
}
```

**Response**
```json
{
  "job_id": "f47ac10b-58cc",
  "status": "queued",
  "estimated_seconds": 2
}
```

**Authentication:** `X-API-Key: sk-safe-XXXXXXXXXX`

---

### `GET /v1/jobs/{job_id}`

Poll for job result.

**Response (complete)**
```json
{
  "status": "complete",
  "url": "https://example.com/public/data",
  "content": "...<scrubbed content>...",
  "pii_redacted": 3,
  "robots_allowed": true,
  "policy_decision": "ALLOW",
  "fetched_at": "2026-03-12T10:00:00Z",
  "credits_remaining": 47
}
```

**Status values:** `queued` · `running` · `complete` · `blocked` · `failed`

---

### `GET /health`

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "database": "connected",
  "redis": "connected"
}
```

---

### Export OpenAPI Schema

```bash
curl http://localhost:8000/openapi.json -o docs/openapi.json
```

---

## Configuration

| Env Var | Default | Description |
|---|---|---|
| `PII_SALT` | *(required)* | HMAC salt for hash mode — use a long random string |
| `PII_MODE` | `redact` | `redact` (→ `[REDACTED]`) or `hash` (HMAC-SHA256) |
| `REDIS_URL` | `redis://redis:6379/0` | Celery broker and result backend |
| `DATA_DIR` | `data` | Directory for SQLite database file |
| `DATABASE_URL` | SQLite | Set to `postgresql://...` for production |
| `MAX_RESPONSE_BYTES` | `5242880` | Max fetch size per URL (5 MB default) |
| `FETCH_TIMEOUT_SECONDS` | `10` | HTTP request timeout |
| `USER_AGENT` | `SafeSaaS/1.0` | User-Agent sent with all requests |
| `DASHBOARD_ADMIN_PASSWORD` | *(blank = disabled)* | Protects admin tab in Streamlit dashboard |
| `CORS_ORIGINS` | *(blank)* | Comma-separated allowed CORS origins |

---

## Security

Security is a first-class concern. Every layer is hardened by design.

### Built-In Protections

| Layer | Protection |
|---|---|
| **Authentication** | API keys stored as SHA-256 hashes — never plaintext |
| **Authorization** | Atomic credit deduction via `UPDATE WHERE credits > 0` — no TOCTOU race |
| **SSRF** | All URLs validated against private IP ranges before any fetch |
| **Size cap** | Streaming fetch with hard byte limit — no memory exhaustion |
| **robots.txt** | Checked before every request — fails closed on network error |
| **PII scrubbing** | In-memory pipeline: email, phone (NA format), SSN, IPv4, credit card |
| **Redirect validation** | Redirect chain verified hop-by-hop |
| **Dashboard** | Admin panel requires password via environment variable |
| **CI pipeline** | Bandit + Trivy + pip-audit run on every push |

### Reporting Vulnerabilities

**Do not open public GitHub issues for security vulnerabilities.**

Email: **security@teosegypt.com**  
Full policy: [SECURITY.md](./SECURITY.md)

We acknowledge within 48 hours and target a fix within 7 days for critical issues.

---

## Compliance

### Data Flow

```
URL submitted → robots.txt check → SSRF validation → fetch
→ PII scrubbed IN MEMORY → clean content stored → audit log written
```

**PII is never persisted.** Scrubbing happens in-memory before any disk write.

### GDPR Posture

- Audit logs retained 90 days (configurable)
- No third-party analytics in the API request path
- Data Processing Agreement available on request → compliance@teosegypt.com
- Right to deletion: contact support@teosegypt.com with your account email

---

## Database Migrations

Schema changes are managed with **Alembic**.

```bash
alembic upgrade head
alembic revision --autogenerate
```

Migration files live in `alembic/versions/`.

---

## Running Tests

```bash
pip install -r requirements.txt pytest httpx
pytest tests/ -v
```

Integration tests cover: policy enforcement · robots.txt blocking · SSRF protection · redirect chain validation.

---

## Self-Hosting vs. Hosted API

| | Self-Hosted | Hosted API |
|---|---|---|
| Setup | Docker Compose | None |
| Data residency | Your servers | Managed cloud |
| Pricing | Free (your infra costs) | Per-URL credits |
| SLA | You manage | 99.9% uptime (paid plans) |
| Support | Community / GitHub Issues | Email |

---

## Pricing

| Plan | Price | URLs | Expiry | Cost / URL |
|---|---|---|---|---|
| **Free Trial** | $0 | 5 | 48 hours | Free |
| **Pay-As-You-Go** | $0.15 / URL | Unlimited | No expiry | $0.15 |
| **Monthly Starter** | $29 / mo | 300 | 30 days | $0.097 |
| **Monthly Growth** | $79 / mo | 900 | 30 days | $0.088 |
| **Yearly Starter** | $290 / yr | 3,000 | 365 days | $0.097 |
| **Yearly Growth** | $790 / yr | 9,000 | 365 days | $0.088 |
| **Enterprise** | Custom | Unlimited | Custom | Custom |

Payment via **USDC on Base network** or Stripe.  
USDC wallet: `0xd9CA11Dde3810a1BA9B5E1a4b6b76F5a419FAb41` *(Base network only — not Ethereum mainnet)*  
→ https://safe.teosegypt.com/#pricing

---

## Documentation

| Document | Purpose |
|---|---|
| [ARCHITECTURE.md](./ARCHITECTURE.md) | System design and data flow |
| [docs/API.md](./docs/API.md) | Full endpoint reference |
| [docs/openapi.json](./docs/openapi.json) | OpenAPI schema |
| [OPERATIONS.md](./OPERATIONS.md) | Runbooks and monitoring |
| [SELF_HOSTING.md](./SELF_HOSTING.md) | Deployment guide |
| [TESTING.md](./TESTING.md) | Test strategy and coverage |
| [COMPLIANCE.md](./COMPLIANCE.md) | Governance and GDPR posture |
| [SECURITY.md](./SECURITY.md) | Vulnerability reporting policy |
| [CHANGELOG.md](./CHANGELOG.md) | Version history and all bug fixes |
| [CONTRIBUTING.md](./CONTRIBUTING.md) | Contribution guidelines |

---

## Example Assets

Evaluation assets included under `examples/`:

```
examples/
├── datasets/      # sample URL sets for testing
├── policies/      # ready-to-use YAML policy templates
└── outputs/       # sanitized ingestion output examples
```

---

## Changelog — 20 Bugs Fixed at Launch

The v1.0.0 release included an audit that identified and fixed 20 bugs across critical, security, and correctness categories. Full details in [CHANGELOG.md](./CHANGELOG.md).

**Critical fixes summary:**
- API keys were stored in plaintext → now SHA-256 hashed
- Credit deduction had a TOCTOU race → now atomic SQL
- SSRF guard was missing from scraper → added with private IP blocklist
- robots.txt was not integrated into PolicyEngine → now enforced on every request
- Core database functions were missing → implemented
- PDF export was blank → fixed via ReportLab
- CI workflow referenced non-existent action versions → pinned to valid releases

---

## Roadmap

- [x] robots.txt compliance
- [x] PII scrubbing (email, phone, SSN, IP, CC)
- [x] SSRF protection
- [x] Full audit log + PDF export
- [x] Async job queue (Celery + Redis)
- [x] YAML policy rules
- [x] Streamlit dashboard with metrics
- [x] USDC micropayment integration (Base network)
- [x] Pay-as-you-go pricing ($0.15/URL, no expiry)
- [x] API key hashing (SHA-256)
- [x] Atomic credit deduction
- [ ] PostgreSQL production backend
- [ ] Webhook callbacks on job completion
- [ ] x402 protocol support (AI agent native payments)
- [ ] OpenAPI SDK (Python, Node.js)
- [ ] Signed audit log exports
- [ ] SOC 2 Type I audit
- [ ] Enterprise SSO

---

## Contributing

Issues, bug reports, and feature requests are welcome.  
See [CONTRIBUTING.md](./CONTRIBUTING.md) for guidelines.

Enterprise licensing: license@teosegypt.com

---

## License

Source-available under a commercial license.  
See [LICENSE](./LICENSE) for full terms.

---

<div align="center">

Built by **Ayman Seif** · [Elmahrosa International](https://teosegypt.com) 🇪🇬 · Est. 2007

**Safe Ingestion Engine** — Scrape the web. Responsibly.  
[safe.teosegypt.com](https://safe.teosegypt.com)

</div>
