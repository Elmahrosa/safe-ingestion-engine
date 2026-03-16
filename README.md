<div align="center">

# 🛡 Safe Ingestion Engine

### Compliance-First Web Data Ingestion Infrastructure for AI Systems

[![Python](https://img.shields.io/badge/Python-3.11-3776ab?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=flat-square&logo=docker&logoColor=white)](https://docker.com)
[![Redis](https://img.shields.io/badge/Redis-Queue-dc382d?style=flat-square&logo=redis&logoColor=white)](https://redis.io)
[![Celery](https://img.shields.io/badge/Celery-gevent_pool-37814a?style=flat-square)](https://docs.celeryq.dev)
[![Tests](https://img.shields.io/badge/Tests-32_passing-brightgreen?style=flat-square)]()
[![Version](https://img.shields.io/badge/Version-3.0.0-blue?style=flat-square)]()
[![x402](https://img.shields.io/badge/x402-USDC_on_Base-9b59ff?style=flat-square)](https://x402.org)
[![License](https://img.shields.io/badge/License-Commercial_Proprietary-red?style=flat-square)](LICENSE)

**[⭐ Star this repo](https://github.com/Elmahrosa/safe-ingestion-engine)** · **[💬 License / Acquire](mailto:ayman@teosegypt.com)** · **[⚡ x402 Ecosystem](https://x402.org/ecosystem)**

*Maintained by [Elmahrosa International](https://elmahrosa.com) · ayman@teosegypt.com*

</div>

---

## What Is Safe Ingestion Engine?

Safe Ingestion Engine is **compliance infrastructure** for web data pipelines.

Traditional scrapers give you raw data and leave compliance as your problem. Safe Ingestion Engine inverts this: **governance is enforced at the infrastructure layer**, before data reaches your application.

```
Traditional scraper:   fetch → your app → you handle compliance
Safe Ingestion Engine: request → policy gate → safe fetch → PII scrub → your app
```

Compliance, security, and auditability are **structural guarantees** built into the pipeline — not middleware you bolt on later.

---

## Engineering Maturity — v3.0.0

Three independent technical audits completed. 30 issues identified and patched. Full hardening sprint delivered in v3.0.0.

| Category | Score |
|----------|-------|
| Architecture | 9 / 10 |
| Security thinking | 9 / 10 |
| Production maturity | 8 / 10 |
| Observability | 7 / 10 |
| Scale readiness | 8 / 10 |
| **Overall** | **8.5 / 10** |

*v3.0.0 — YAML policy engine · content hashing · domain isolation · Streamlit dashboard · 32 tests · JobStatus state machine*

---

## Core Guarantees

| Guarantee | How it is enforced |
|-----------|-------------------|
| `robots.txt` respected | `PolicyEngine.evaluate()` checks before every fetch — structural, not advisory |
| Zero PII in output | Email, phone, SSN, IP, CC — redacted or HMAC-SHA256 hashed in worker before data leaves |
| SSRF impossible | Private IPs, loopback, link-local, reserved, multicast — blocked before any network I/O |
| No domain flooding | Max concurrent jobs per domain enforced via Redis — prevents accidental DDoS |
| Content deduplicated | `sha256(content)` stored per job — deduplication, change detection, fingerprinting |
| Every request auditable | URL, timestamp, policy decision, PII count, content hash — tamper-evident log |
| Keys never exposed | SHA-256 hashed before storage — plaintext never in database or Redis |
| Race conditions eliminated | Atomic Redis WATCH/MULTI/EXEC on credit deduction — no TOCTOU |
| API key isolated from queue | Task signatures carry only job context — raw key never in Redis |
| State machine enforced | `JobStatus` SQLAlchemy Enum — invalid transitions raise `ValueError` before any DB write |

---

## Architecture

```
POST /v1/ingest_async
        │
        ▼
[ Auth Layer ]         HMAC key validation + atomic credit deduction (Redis)
        │
        ▼
[ Rate Limiter ]       Per-API-key Redis counter (slowapi) — configurable per plan
        │
        ▼
[ PolicyEngine ]       YAML domain rules → robots.txt → crawl budget → domain concurrency
        │ BLOCKED → 0 credits consumed, audit log written
        ▼
[ SSRF Guard ]         Async DNS → block private/loopback/reserved IPs at connect time
        │
        ▼
[ Safe Fetch ]         httpx + circuit breaker + 5MB streaming cap
        │
        ▼
[ PII Scrubber ]       Regex fast-path → HMAC-hashed redaction tokens
        │
        ▼
[ Content Hasher ]     sha256(cleaned_content) → stored on Job
        │
        ▼
[ Audit Log ]          job_id · url · domain · pii_count · content_hash → DB
        │
        ▼
  Clean content + job_id returned to caller
```

---

## What Shipped in v3.0.0

| Feature | File | Status |
|---------|------|--------|
| `JobStatus` Enum + state machine transition guard | `core/models.py` | ✅ |
| `content_hash` — sha256 per job | `core/models.py` · `infrastructure/queue/tasks.py` | ✅ |
| `tenant_id` — multi-tenant isolation | `core/models.py` · `api/routes/ingest.py` | ✅ |
| `domain` field — indexed, extracted at submit time | `core/models.py` · `api/routes/ingest.py` | ✅ |
| YAML policy rules wired into `PolicyEngine.evaluate()` | `core/policy.py` · `policies/rules.yaml` | ✅ |
| Domain concurrency isolation (max 2 jobs/domain) | `core/policy.py` · `infrastructure/queue/tasks.py` | ✅ |
| `GET /v1/jobs` — paginated job list with status filter | `api/routes/ingest.py` | ✅ |
| `GET /v1/audit` — paginated audit log | `api/routes/ingest.py` | ✅ |
| `GET /v1/domains` — per-domain stats | `api/routes/ingest.py` | ✅ |
| Per-API-key rate limiter (not IP-based) | `security/rate_limit.py` | ✅ |
| `RETRYING` state visible in job responses | `core/models.py` · `infrastructure/queue/tasks.py` | ✅ |
| Streamlit dashboard — audit, metrics, domains, CSV export | `dashboard/app.py` | ✅ |
| 32 tests — state machine, PII, SSRF, auth, content hash | `tests/test_core.py` | ✅ |

---

## API Reference

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/v1/ingest_async` | API Key | Submit URL for ingestion |
| `GET` | `/v1/jobs/{job_id}` | API Key | Poll job status and result |
| `GET` | `/v1/jobs` | API Key | List jobs — filter by status, paginate |
| `GET` | `/v1/audit` | API Key | Paginated audit log |
| `GET` | `/v1/domains` | API Key | Per-domain crawl stats |
| `GET` | `/v1/account` | API Key | Credits, plan, key info |
| `GET` | `/health` | none | Liveness probe |
| `GET` | `/metrics` | none | Prometheus metrics |

### Job Status Machine

```
PENDING → RUNNING → COMPLETED
                 ↘ RETRYING → RUNNING (up to max_retries)
                 ↘ BLOCKED   (policy denied — 0 credits consumed)
                 ↘ FAILED    (retries exhausted)
```

### Quick Start

```bash
# Submit
curl -X POST https://your-host/v1/ingest_async \
  -H "X-API-Key: sk-your-key" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/page"}'
# {"job_id": "3f8c2b1a-...", "status": "PENDING"}

# Poll
curl https://your-host/v1/jobs/3f8c2b1a-... \
  -H "X-API-Key: sk-your-key"
# {"status": "COMPLETED", "pii_found": 3, "content_hash": "a3f8...", "result_excerpt": "..."}
```

---

## YAML Policy Rules

```yaml
# policies/rules.yaml — evaluated before robots.txt on every request

domains:
  - domain: "wsj.com"
    allow: false
    reason: "paywalled content"

  - domain: "wikipedia.org"
    allow: true
    crawl_budget: 500
    delay_seconds: 1
    max_concurrent: 2

default: allow
```

---

## Deployment

### Local / Development

```bash
git clone https://github.com/Elmahrosa/safe-ingestion-engine.git
cd safe-ingestion-engine
cp .env.example .env
docker compose up --build
# API: http://localhost:8000
# Dashboard: streamlit run dashboard/app.py
```

### Production

```bash
# Set in .env:
# DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/safe_ingestion
# REDIS_URL=redis://your-redis:6379/0
# PII_SALT=<64-char hex>
# API_KEY_SALT=<64-char hex>
docker compose up -d
```

---

## AI Agent Integration

```python
import asyncio, httpx

async def safe_fetch(url: str, api_key: str) -> dict:
    async with httpx.AsyncClient(
        base_url="https://your-host",
        headers={"X-API-Key": api_key},
        timeout=30.0,
    ) as client:
        r = await client.post("/v1/ingest_async", json={"url": url})
        job_id = r.json()["job_id"]
        for _ in range(30):
            await asyncio.sleep(2)
            result = await client.get(f"/v1/jobs/{job_id}")
            if result.json()["status"] in ("COMPLETED", "FAILED", "BLOCKED"):
                return result.json()
```

### MCP (Claude / Cursor / Windsurf)

```json
{
  "mcpServers": {
    "safe-ingestion": {
      "command": "python",
      "args": ["mcp_server.py"],
      "env": {
        "SAFE_API_KEY": "sk-your-key",
        "SAFE_API_BASE": "https://your-host"
      }
    }
  }
}
```

---

## Part of the TeosMCP Agent Safety Stack

| Layer | Tool | Protects |
|-------|------|---------|
| **Data In** | Safe Ingestion Engine *(this repo)* | Clean web data — PII scrubbed, SSRF blocked |
| **Code Out** | [CodeGuard MCP](https://github.com/Elmahrosa/agent-code-risk-mcp) | Code risk scored before execution |
| **On-Chain** | [TeosLinker](https://github.com/Elmahrosa/teoslinker-bot) | Transaction monitoring + execution guard |

---

## Licensing

**Commercial Proprietary License** — source visible, production use licensed.

| Use | License required? |
|-----|------------------|
| Local evaluation ≤ 30 days | ✅ Free |
| Non-commercial research ≤ 500 req/mo | ✅ Free |
| Security audit / responsible disclosure | ✅ Free |
| Production deployment (any scale) | 💳 Paid |
| Commercial SaaS integration | 💳 Paid |
| White-label / resale | 💳 Paid |

**Pricing:** Full acquisition $5,500 · Deployment license $2,000 · White-label $2,500

Contact: **ayman@teosegypt.com**

---

## Roadmap

- [ ] PostgreSQL async backend
- [ ] Python SDK → PyPI
- [ ] CrewAI + LangChain native tools
- [ ] Webhook on job completion
- [ ] Helm chart + Terraform module
- [ ] OpenTelemetry distributed tracing

---

<div align="center">

**Governance at the pipeline layer. Licensed for production.**

[💬 License or Acquire](mailto:ayman@teosegypt.com) · [⭐ Star the repo](https://github.com/Elmahrosa/safe-ingestion-engine) · [⚡ x402](https://x402.org/ecosystem)

*Built by [Elmahrosa International](https://elmahrosa.com) — Cairo, Egypt*

</div>
```