<div align="center">

# 🛡 Safe Ingestion Engine

[![Python](https://img.shields.io/badge/Python-3.11-blue)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688)](https://fastapi.tiangolo.com)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ed)](https://docker.com)
[![Security](https://img.shields.io/badge/Security-Safe_by_Design-2ea043)](#security-model)
[![Trial](https://img.shields.io/badge/Trial-48h_Free-9b59ff)](https://safe.teosegypt.com)
[![Live](https://img.shields.io/badge/Live-safe.teosegypt.com-00d4aa)](https://safe.teosegypt.com)
[![Ko-fi](https://img.shields.io/badge/Support-Ko--fi-ff5f5f)](https://ko-fi.com/elmahrosa)

**Compliance-first infrastructure for safe web data ingestion**

Safe Ingestion Engine is an ingestion control layer for collecting web data with built-in policy enforcement, SSRF protection, PII scrubbing, and audit logging.

🌐 **Live:** https://safe.teosegypt.com  
⏱ **48-hour free trial — no card, no KYC, no auto-billing**  
📬 **Contact:** aams1969@gmail.com

</div>

---

## Overview

Most scraping tools optimize for speed.

**Safe Ingestion Engine optimizes for safety, governance, and auditability.**

```text
URL → Policy Engine → Safe Fetch → PII Scrubber → Clean Content + Audit Log
```

Every ingestion request is evaluated for:

- robots.txt compliance
- YAML domain policy rules
- SSRF safety
- redirect chain safety
- response size limits
- PII protection before storage

---

## Why It Exists

Safe Ingestion Engine is designed for teams that need to collect web data while keeping compliance and security controls in the path by default.

It helps you:

- respect `robots.txt` before fetching
- enforce allow/deny rules per domain
- block SSRF and unsafe redirects
- scrub sensitive data before storage
- maintain audit evidence for every request
- operate ingestion workflows with safer defaults

---

## Architecture

```text
FastAPI Gateway (api.py)
        │  X-API-Key validation via remote provisioning
        ▼
run_ingestion() (main.py)
        │
        ├── PolicyEngine (core/policy.py)
        │     ├── robots.txt validation
        │     ├── YAML allow/deny rules
        │     └── per-domain crawl budgets
        │
        ├── SafeScraper (collectors/scraper.py)
        │     ├── SSRF protection
        │     ├── DNS resolution validation
        │     ├── redirect-chain validation
        │     └── response size cap
        │
        └── PIIScrubber (core/pii.py)
              ├── email, phone, IP detection
              └── card / sensitive pattern scrubbing
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
```

**Stack:** Python 3.11 · FastAPI · Celery · Redis · SQLite · Streamlit · Docker

---

## Core Components

### Policy Engine
Governs whether a request is allowed to proceed. Enforces robots.txt, YAML domain rules, daily per-domain crawl budgets, and optional defaults such as weekend blocking.

### SafeScraper
Network-safe fetch layer with SSRF blocking, hostname and DNS resolution checks, redirect-chain validation, response streaming with hard byte caps, and rate limiting.

### PIIScrubber
Removes or pseudonymizes sensitive data before content is stored. Detects emails, phone numbers, IP addresses, and payment-card patterns. Supports `redact` and `hash` modes.

### Audit Log
Every ingestion outcome is recorded with URL, status, reason, timestamp, latency, bytes, and content type — providing compliance evidence and operational traceability.

### Dashboard
Streamlit-based operational view covering audit history, performance metrics, stored ingestion results, and exportable CSV / PDF reports.

---

## API Reference

All protected endpoints require:

```
X-API-Key: your-key
```

### `POST /v1/ingest_async`

Queue an ingestion job. Returns immediately.

**Request**
```json
{ "url": "https://example.com" }
```

**Response**
```json
{
  "ok": true,
  "status": "accepted",
  "task_id": "uuid",
  "account": "user@example.com",
  "plan_name": "Growth"
}
```

### `GET /v1/me`

Return account metadata for the authenticated API key.

```json
{
  "ok": true,
  "email": "user@example.com",
  "plan_name": "Growth",
  "cycle": "month",
  "account_type": "PAID",
  "payment_status": "ACTIVE",
  "expires_at": "2026-12-31",
  "status": "ACTIVE"
}
```

### `GET /healthz`

Health check — no auth required.

```json
{ "status": "ok" }
```

### `POST /ingest` *(legacy)*

Backward-compatible alias for `/v1/ingest_async`.

---

## Quick Start

### Hosted API

Sign up at https://safe.teosegypt.com and receive your API key by email.

```bash
curl -X POST https://safe.teosegypt.com/v1/ingest_async \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'

curl https://safe.teosegypt.com/v1/me \
  -H "X-API-Key: your-key"
```

### Self-Host with Docker

```bash
git clone https://github.com/Elmahrosa/safe-ingestion-engine.git
cd safe-ingestion-engine
cp .env.example .env
docker compose up -d
```

API on `http://localhost:8000` · Dashboard on `http://localhost:8501`

---

## Configuration

Copy `.env.example` to `.env`:

| Variable | Description |
|----------|-------------|
| `SIE_PROVISIONING_URL` | Remote endpoint used to validate API keys |
| `SIE_PROVISIONING_SECRET` | Shared secret for provisioning calls |
| `DATA_DIR` | SQLite storage directory |
| `REDIS_URL` | Redis broker URL |
| `USER_AGENT` | Scraper user-agent string |
| `MAX_RESPONSE_BYTES` | Hard response size cap |
| `FETCH_TIMEOUT_SECONDS` | HTTP timeout |
| `MAX_REDIRECTS` | Maximum allowed redirect hops |
| `PII_MODE` | `redact` or `hash` |
| `PII_SALT` | Salt for hash mode |
| `DASHBOARD_ADMIN_PASSWORD` | Protects the admin dashboard tab |
| `CORS_ORIGINS` | Allowed frontend origins |

---

## Policy Rules

Edit `policies/policy.yml`:

```yaml
version: 1

defaults:
  max_requests_per_domain_per_day: 20
  min_seconds_between_requests: 2
  max_bytes: 2000000
  block_weekends: false

domains:
  - match: "*.gov"
    action: deny
    note: "Sensitive TLD pattern"

  - match: "www.example.com"
    action: allow
    note: "Explicitly permitted"
```

---

## Security Model

| Control | Implementation |
|---------|----------------|
| SSRF blocking | Private, loopback, link-local, reserved, and metadata IPs blocked |
| Redirect safety | Redirect chain revalidated hop-by-hop |
| robots.txt enforcement | Checked before every fetch |
| Policy rules | YAML-driven allow/deny and crawl budgets |
| Response limits | Stream aborted if max bytes exceeded |
| PII protection | Sensitive patterns scrubbed before storage |
| API key handling | Validated via remote provisioning; masked in logs |
| Container hardening | Non-root Docker user |
| Gateway enforcement | `401` for invalid keys · `402` for expired or inactive states |

CI scanning: **Bandit · Semgrep · Safety** — see `.github/workflows/security.yml`

---

## Running Tests

```bash
pip install -r requirements.txt
pytest tests/ -v
```

Covers: PII scrubbing, SSRF blocking, database helpers, policy engine decisions.

---

## Changelog — v1.0.0

| # | Severity | Fix |
|---|----------|-----|
| 1 | 🔴 Critical | Added missing credit deduction logic |
| 2 | 🔴 Critical | Fixed broken audit log retrieval |
| 3 | 🔴 Critical | Resolved PDF export failure |
| 4 | 🔴 Critical | Fixed API key validation returning `None` |
| 5 | 🔴 Critical | Corrected robots.txt cache logic |
| 6 | 🔴 Critical | Patched TOCTOU race condition in usage deduction |
| 7 | 🔐 Security | API keys now SHA-256 hashed |
| 8 | 🔐 Security | SSRF protection added |
| 9 | 🔐 Security | 5MB response size cap |
| 10 | 🔐 Security | Admin routes password-protected |
| 11 | 🔐 Security | Atomic credit deduction |
| 12–20 | 🟡 Quality | DB lifecycle, PII regex, Celery tasks, PDF export, Docker ordering |

---

## x402 Payment Gate

Safe Ingestion Engine is structured around an **x402-style payment gate architecture** for controlled paid activation.

Current state:

- automatic trial provisioning
- automatic API key issuance by email
- remote key validation at the gateway layer
- `401` for invalid auth
- `402`-compatible denial for expired, inactive, or gated states

See `docs/x402-gate.md` for full details.

---

## Roadmap

- PostgreSQL production backend
- Webhook callbacks for job completion
- Signed audit export bundles
- Richer usage analytics
- Stronger tenant isolation
- Advanced per-plan policy controls

---

## Pricing

48-hour free trial on all plans — no card, no KYC, no auto-billing.

| Plan | Price | URLs |
|------|-------|------|
| Trial | Free | 20 |
| Monthly Starter | $29/mo | 300 |
| Monthly Growth | $79/mo | 900 |
| Yearly Starter | $290/yr | 3,000 |
| Yearly Growth | $790/yr | 9,000 |

Full pricing and activation at https://safe.teosegypt.com

---

## Support

| Platform | Link |
|----------|------|
| ☕ Ko-fi | [ko-fi.com/elmahrosa](https://ko-fi.com/elmahrosa) |
| ❤️ GitHub Sponsors | [github.com/sponsors/Elmahrosa](https://github.com/sponsors/Elmahrosa) |
| 🍵 Buy Me a Coffee | [buymeacoffee.com/elmahrosa](https://buymeacoffee.com/elmahrosa) |
| 💼 Consulting | aams1969@gmail.com |

---

## License

**Proprietary** — see [LICENSE](LICENSE) for full terms.

---

## Contact

| | |
|-|-|
| 🌐 Website | [safe.teosegypt.com](https://safe.teosegypt.com) |
| 📧 Email | aams1969@gmail.com |
| 🏢 Company | [teosegypt.com](https://teosegypt.com) |

---

<div align="center">

**Built by Ayman Seif · Elmahrosa International 🇪🇬**

[⏱ Start Free Trial](https://safe.teosegypt.com) · [☕ Ko-fi](https://ko-fi.com/elmahrosa) · [❤️ GitHub Sponsors](https://github.com/sponsors/Elmahrosa)

</div>
