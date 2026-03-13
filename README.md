<div align="center">

# 🛡 Safe Ingestion Engine

### Compliance-First Web Data Ingestion Infrastructure for AI Systems

[![CI](https://github.com/Elmahrosa/safe-ingestion-engine/actions/workflows/ci.yml/badge.svg)](https://github.com/Elmahrosa/safe-ingestion-engine/actions)
[![Security Scan](https://github.com/Elmahrosa/safe-ingestion-engine/actions/workflows/security.yml/badge.svg)](https://github.com/Elmahrosa/safe-ingestion-engine/actions)
[![Python](https://img.shields.io/badge/Python-3.11-3776ab?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=flat-square&logo=docker&logoColor=white)](https://docker.com)
[![Redis](https://img.shields.io/badge/Redis-Queue-dc382d?style=flat-square&logo=redis&logoColor=white)](https://redis.io)
[![x402](https://img.shields.io/badge/x402-USDC_on_Base-9b59ff?style=flat-square)](https://x402.org)
[![License](https://img.shields.io/badge/License-Commercial_Proprietary-red?style=flat-square)](LICENSE)

**[🌐 Platform](https://safe.teosegypt.com)** · **[📚 API Docs](https://safe.teosegypt.com/docs.html)** · **[⚡ x402 Ecosystem](https://x402.org/ecosystem)** · **[💬 Enterprise Licensing](mailto:ayman@teosegypt.com)**

*Maintained by [Elmahrosa International](https://elmahrosa.com) · ayman@teosegypt.com*

</div>

---

## What Is Safe Ingestion Engine?

Safe Ingestion Engine is **compliance infrastructure** for web data pipelines.

Source visible. Security auditable. Production use licensed.

Traditional scrapers give you raw data and leave compliance as your problem. Safe Ingestion Engine inverts this: **governance is enforced at the infrastructure layer**, before data reaches your application.

```
Traditional scraper:   fetch → your app → you handle compliance
Safe Ingestion Engine: request → policy gate → safe fetch → PII scrub → your app
```

Compliance, security, and auditability are **structural guarantees** built into the pipeline — not middleware you bolt on later and forget to configure.

---

## Core Guarantees

| Guarantee | How it is enforced |
|-----------|-------------------|
| `robots.txt` respected | `PolicyEngine` checks before every fetch — structural, not advisory. Request never reaches the fetcher if denied. |
| Zero PII in output | Emails, phones, SSNs, IPs, credit cards — redacted to `[REDACTED]` or HMAC-SHA256 hashed. Runs in worker before data leaves. |
| SSRF impossible | Private IP ranges `10.x`, `172.16.x`, `192.168.x`, `127.x`, `169.254.x`, `::1`, multicast, reserved — blocked at URL validation, before any network I/O. DNS rebinding gap patched via connect-time IP revalidation. |
| Every request auditable | Tamper-evident log: URL, timestamp, policy decision, PII redaction count, latency, outcome. PDF exportable. |
| No payment replay | x402 tx hash deduplicated — in-memory for dev, Redis-persisted with TTL for production. |
| Keys never exposed | SHA-256 hashed before storage — plaintext never written to the database. |
| Race conditions eliminated | Atomic `UPDATE WHERE credits > 0` — no TOCTOU on credit deduction. Verified by rowcount check. |
| API key isolated from queue | Worker task signatures carry only job context — never the raw API key. |

---

## Architecture

```mermaid
flowchart LR
    Client["Client / AI Agent"]
    GW["x402 Payment Gate"]
    API["FastAPI API\n+ Auth Middleware"]
    Q["Redis Queue\n(job context only)"]
    W["Celery Workers\n(gevent pool)"]
    P["PolicyEngine\nrobots.txt + YAML rules\n+ crawl budget"]
    F["Safe Fetcher\nSSRF + DNS rebind guard\n5MB streaming cap"]
    S["PII Pipeline\nregex patterns + Presidio\nredact / HMAC-hash"]
    DB[("Audit Database\nSQLite → PostgreSQL")]
    DASH["Monitoring Dashboard\nStreamlit + PDF export"]

    Client --> GW --> API --> Q --> W
    W --> P --> F --> S --> DB --> DASH
```

### Full request pipeline

```
[Request received]
        │
        ▼
[x402 Gate] ─── bypass: test / owner / bot ──────────────────────────────┐
        │  tx hash format validated → on-chain verify (optional)          │
        │  tx hash deduplicated (Redis set, 90-day TTL)                  │
        ▼                                                                  │
[Auth Middleware] ─── SHA-256(api_key) lookup → atomic credit deduction   │
        │  rowcount check eliminates TOCTOU race                          │
        │  api_key NOT passed to task queue                               │
        ▼                                                                  │
[PolicyEngine] ─── YAML domain rules → robots.txt → crawl budget          │
        │  ALLOW                          │  BLOCK → HTTP 403             │
        ▼                                                                  │
[Safe Fetcher] ─── SSRF guard → DNS rebind check at connect time          │
        │  5MB streaming cap → timeout enforced                           │
        ▼                                                                  │
[PII Pipeline] ─── regex patterns (email, phone, SSN, IP, CC)             │
        │  + Microsoft Presidio (NLP) for names, passports, dates         │
        │  configurable: redact [REDACTED] or HMAC-SHA256 hash            │
        ▼                                                                  │
[Audit Log] ─── structured record per request  ◄──────────────────────────┘
        │  SQLite (dev) → PostgreSQL (production)
        ▼
[Response → Client]
```

---

## Repository Structure

```
safe-ingestion-engine/
│
├── api/
│   ├── server.py          # FastAPI app · routes · x402 middleware · auth · atomic credits
│   └── tasks.py           # Celery tasks · gevent pool · retry with jitter · NO api_key in payload
│
├── collectors/
│   └── scraper.py         # Safe fetcher · SSRF guard · DNS rebind protection · 5MB streaming cap
│
├── core/
│   ├── database.py        # log_audit() · log_metrics() · insert_raw() · session_scope() context manager
│   ├── pii.py             # Primary PII pipeline: regex scrubber + Presidio NLP integration
│   ├── pii_ai.py          # Presidio wrapper: names, passports, national IDs, dates of birth
│   └── policy.py          # PolicyEngine: YAML rules + robots.txt + per-domain crawl budget (Redis)
│
├── dashboard/
│   └── app.py             # Streamlit: audit log · metrics KPIs · PDF export · password-protected admin
│
├── policies/
│   └── rules.yaml         # Per-domain allow/deny · path blocking · crawl budgets · delays (wired into PolicyEngine)
│
├── tests/
│   ├── test_api.py        # FastAPI endpoint coverage
│   ├── test_pii.py        # PII pattern tests (email, phone, SSN, IP, CC, names)
│   ├── test_policy.py     # PolicyEngine: allow, deny, robots.txt, crawl budget
│   └── test_scraper.py    # SSRF guard tests across all private ranges
│
├── .github/
│   └── workflows/
│       ├── ci.yml         # pytest + coverage on every push
│       └── security.yml   # Bandit + Semgrep + Trivy (pinned to @v4/@v5)
│
├── .env.example           # All variables documented with defaults and explanations
├── Dockerfile             # Non-root user · minimal base · production hardened
├── docker-compose.yml     # Full stack · healthchecks · worker waits for Redis ready
├── main.py                # Uvicorn entry point · load_dotenv() inside __main__ guard
└── requirements.txt       # Pinned dependencies
```

---

## What Was Fixed — Security & Code Audit

This codebase has been through two independent security and code audits. All identified issues are patched in the current version.

### Security Fixes

| # | File | Issue | Fix Applied |
|---|------|-------|-------------|
| 1 | `api/tasks.py` | Raw API key serialized into Celery task payload → stored in Redis | Key removed from task signature entirely — only job context passed |
| 2 | `collectors/scraper.py` | SSRF DNS rebinding: hostname validated once, then re-resolved at connect time | IP revalidated at connect time using custom `httpx` transport |
| 3 | `api/server.py` | Credit deduction had TOCTOU race — two concurrent requests could both pass `credits > 0` | Atomic `UPDATE WHERE credits > 0` + rowcount check |
| 4 | `api/server.py` | API keys stored and compared in plaintext | SHA-256 hashed before storage and lookup |
| 5 | `core/policy.py` | `policies/rules.yaml` parsed but not wired into `PolicyEngine.evaluate()` — dead config, false security | YAML domain rules now enforced at evaluate() before robots.txt check |
| 6 | `core/compliance.py` | robots.txt logic duplicated across `compliance.py` and `policy.py` with different failure semantics | Consolidated into `PolicyEngine` — `compliance.py` repurposed for `is_safe_url()` only |
| 7 | `dashboard/app.py` | Admin section exposed all user data with no authentication | Password-protected via `DASHBOARD_ADMIN_PASSWORD` env var |
| 8 | `collectors/scraper.py` | No response size cap — large responses could exhaust worker memory | Streaming fetch with 5MB hard limit |
| 9 | `.github/workflows/security.yml` | `actions/checkout@v6` and `setup-python@v6` don't exist | Pinned to `@v4` / `@v5` · Trivy container scan added |
| 10 | `main.py` | `load_dotenv()` called on every import, overriding env vars in Docker | Moved inside `if __name__ == "__main__"` guard |

### Code Quality Fixes

| # | File | Issue | Fix Applied |
|---|------|-------|-------------|
| 11 | `api/tasks.py` | `asyncio.run()` inside Celery worker — new event loop per task, resource wasteful | Worker pool converted to `gevent` · `httpx` used in sync mode |
| 12 | `core/pii.py` | `PIIScrubber` instantiated fresh on every call — class overhead per request | `scrub_text()` is now a module-level function calling compiled regex directly |
| 13 | `core/pii.py` | Only 3 PII patterns: email, phone, credit card — SSN, IPv4, names, passports missed | Added SSN `\b\d{3}-\d{2}-\d{4}\b` · IPv4 · Presidio NLP integrated as primary scanner |
| 14 | `core/policy.py` | `Job.status` plain string — no Enum, no transition guard, accepts any value | `SQLAlchemy Enum` type with state machine guard in service layer |
| 15 | `api/tasks.py` | DB connection opened but never closed (success path) | `try/finally conn.close()` |
| 16 | `core/compliance.py` | `except:` silently returned BLOCKED on any exception including network timeouts | Fail-open with logged warning |
| 17 | `dashboard/app.py` | PDF export was a blank page | Exports actual audit table via ReportLab platypus |
| 18 | `dashboard/app.py` | `request_metrics` table had no dashboard view | Metrics tab with KPI cards |
| 19 | `docker-compose.yml` | No healthchecks — worker could start before Redis was ready | `healthcheck` + `condition: service_healthy` |
| 20 | `api/server.py` | No job list endpoint — only GET by ID | `GET /v1/jobs?status=&page=` pagination endpoint added |
| 21 | `api/tasks.py` + `api/server.py` | `result_excerpt` truncated at 2000 chars in task, again at 500 in API response | Single authoritative truncation in task · configurable via `MAX_EXCERPT_CHARS` env var |
| 22 | `core/pii.py` | Presidio (`pii_ai.py`) existed as standalone utility, never integrated | `detect_pii_ai()` now runs as primary scanner · regex as fast-path fallback |

---

## Deployment

### Local / Development

```bash
git clone https://github.com/Elmahrosa/safe-ingestion-engine.git
cd safe-ingestion-engine

cp .env.example .env
# Minimum: set PII_SALT and DASHBOARD_ADMIN_PASSWORD

TEOS_MODE=test docker compose up --build

# API:       http://localhost:8000/docs
# Dashboard: http://localhost:8501
```

### Production (single node)

```bash
cp .env.example .env

# Set in .env before starting:
# TEOS_MODE=production
# VERIFY_ON_CHAIN=true
# RPC_URL=https://mainnet.base.org
# WALLET_ADDRESS=0xd9CA11Dde3810a1BA9B5E1a4b6b76F5a419FAb41
# CORS_ORIGINS=https://yourdomain.com
# DATABASE_URL=postgresql+asyncpg://user:pass@host/db

docker compose up -d
```

### Distributed Cluster

```
Load Balancer
     │
     ├── FastAPI API (node 1)
     ├── FastAPI API (node 2)
     └── FastAPI API (node n)
              │
        Redis Cluster
              │
     ├── Celery Worker (gevent, 1)
     ├── Celery Worker (gevent, 2)
     └── Celery Worker (gevent, n)  ← scale independently
              │
    PostgreSQL Primary
              └── PostgreSQL Replica
```

Workers use `gevent` pool — each worker handles async I/O without blocking threads. Scale the worker tier independently from the API tier.

### Enterprise Cloud

```
Edge Gateway / CDN
        │
   API Gateway + WAF
        │
FastAPI Services (k8s, autoscaled)
        │
Redis HA Cluster (sentinel / cluster mode)
        │
Celery Workers (HPA by queue depth)
        │
PostgreSQL HA (primary + read replicas)
        │
Observability
  ├── Prometheus + Grafana     (metrics via /metrics endpoint)
  ├── Structured JSON → Loki  (structlog throughout)
  └── OpenTelemetry            (distributed tracing, Phase 4)
```

---

## Configuration Reference

```env
# ── REQUIRED ───────────────────────────────────────────────────────────────
PII_SALT=your-hmac-salt-minimum-32-characters
DASHBOARD_ADMIN_PASSWORD=strong-password-here

# ── x402 PAYMENT ───────────────────────────────────────────────────────────
WALLET_ADDRESS=0xd9CA11Dde3810a1BA9B5E1a4b6b76F5a419FAb41
VERIFY_ON_CHAIN=true               # confirm USDC amount on Base RPC
RPC_URL=https://mainnet.base.org
TEOS_MODE=production               # "test" disables payment gate for dev/CI

# ── DEV / BOT BYPASS ───────────────────────────────────────────────────────
TEOS_OWNER_ID=                     # Telegram numeric ID → X-Teos-Owner-Id header
TEOS_BOT_KEY=                      # shared secret → X-Teos-Bot-Key header

# ── PII PIPELINE ───────────────────────────────────────────────────────────
PII_MODE=redact                    # "redact" → [REDACTED] | "hash" → HMAC-SHA256
PII_USE_PRESIDIO=true              # enable Microsoft Presidio NLP scanner
PII_SALT=                          # HMAC salt (required for hash mode)

# ── SCRAPER ────────────────────────────────────────────────────────────────
USER_AGENT=SafeIngestionEngine/1.0
MAX_RESPONSE_BYTES=5242880         # 5MB hard cap (streaming)
FETCH_TIMEOUT_SECONDS=10
MAX_EXCERPT_CHARS=2000             # single authoritative truncation point

# ── CELERY ─────────────────────────────────────────────────────────────────
CELERY_POOL=gevent                 # gevent (recommended) | prefork | solo
CELERY_CONCURRENCY=10              # gevent greenlets per worker process

# ── INFRASTRUCTURE ─────────────────────────────────────────────────────────
REDIS_URL=redis://redis:6379/0
DATABASE_URL=                      # PostgreSQL DSN — overrides SQLite when set
DATA_DIR=data                      # SQLite directory (dev only)
CORS_ORIGINS=                      # comma-separated — blank = all (lock down in prod)
```

---

## API Reference

### Endpoints

| Method | Path | Auth | Cost | Description |
|--------|------|------|------|-------------|
| `POST` | `/v1/ingest_async` | API Key + Payment | `$0.25 USDC` | Submit URL for ingestion |
| `GET` | `/v1/jobs/{job_id}` | API Key | free | Poll job status and result |
| `GET` | `/v1/jobs` | API Key | free | List jobs with filters and pagination |
| `GET` | `/v1/balance` | API Key | free | Credits, plan, trial status |
| `GET` | `/v1/audit` | API Key | free | Paginated audit log |
| `POST` | `/v1/scan-dependencies` | API Key + Payment | `$0.25 USDC` | Deep dependency scan |
| `GET` | `/metrics` | internal | free | Prometheus metrics endpoint |
| `GET` | `/health` | none | free | Liveness probe |
| `GET` | `/ready` | none | free | Readiness probe |

### Job Status Machine

```
queued → processing → completed
                   ↘ blocked      (policy denied)
                   ↘ failed       (fetch/pipeline error)
```

Status is an enforced `SQLAlchemy Enum` — invalid transitions raise a `ValueError` at the service layer before any DB write.

### Job List Endpoint

```bash
# List recent failed jobs, paginated
GET /v1/jobs?status=failed&page=1&per_page=20

# List all completed jobs
GET /v1/jobs?status=completed&page=1
```

### x402 AI Agent Integration

```python
"""
Safe Ingestion Engine — x402 Agent Integration
Autonomous payment: agent pays $0.25 USDC on Base, receives PII-clean data.
Compatible with: CrewAI, AutoGPT, LangChain, n8n, any HTTP-capable agent.
"""
import requests, time

class SafeIngestionTool:
    BASE = "https://safe.teosegypt.com"

    def fetch(self, url: str, agent_wallet) -> dict:
        # First attempt — discover pricing via HTTP 402
        r = requests.post(f"{self.BASE}/v1/ingest_async",
            json={"url": url, "scrub_pii": True})

        if r.status_code == 402:
            info = r.json()
            # Agent pays autonomously — zero human involvement
            tx_hash = agent_wallet.pay_usdc(
                to=info["wallet"],
                amount=info["amount"],  # 0.25 USDC
                network="base"
            )
            r = requests.post(f"{self.BASE}/v1/ingest_async",
                headers={"X-Payment": tx_hash},
                json={"url": url, "scrub_pii": True})

        return self._poll(r.json()["job_id"])

    def _poll(self, job_id: str, timeout: int = 60) -> dict:
        deadline = time.time() + timeout
        while time.time() < deadline:
            result = requests.get(f"{self.BASE}/v1/jobs/{job_id}").json()
            if result["status"] in ("completed", "failed", "blocked"):
                return result
            time.sleep(1)
        raise TimeoutError(f"Job {job_id} did not complete in {timeout}s")
```

---

## YAML Policy Rules

```yaml
# policies/rules.yaml — wired into PolicyEngine.evaluate()
# Evaluated before robots.txt check on every request.

domains:
  # Block a domain entirely — no robots.txt check, no fetch
  - domain: "paywalled-site.com"
    allow: false
    reason: "content not freely available"

  # Block specific paths on an otherwise allowed domain
  - domain: "news-site.com"
    allow: true
    blocked_paths:
      - "/premium/"
      - "/subscriber-only/"
    crawl_budget: 200       # max URLs per day
    delay_seconds: 2        # polite crawl delay between requests

  # Full allow with high crawl budget
  - domain: "docs.python.org"
    allow: true
    crawl_budget: 2000
    delay_seconds: 0.5

# Default for all unlisted domains (robots.txt always enforced regardless)
default: allow
```

---

## Security Model

| Layer | Protection |
|-------|-----------|
| **SSRF** | `10.x`, `172.16.x`, `192.168.x`, `127.x`, `169.254.x`, `::1`, multicast, reserved — blocked |
| **DNS rebinding** | IP revalidated at connect time via custom `httpx` transport — not just at URL validation |
| **Response cap** | 5MB streaming hard limit — prevents memory exhaustion |
| **robots.txt** | PolicyEngine check before every fetch — structural, never advisory |
| **YAML rules** | Per-domain allow/deny and path blocking — enforced before robots.txt |
| **PII pipeline** | Regex (fast path) + Presidio NLP (deep scan) — email, phone, SSN, IP, CC, names, passports |
| **x402 replay** | TX hash dedup set — in-memory (dev), Redis 90-day TTL (prod) |
| **On-chain verify** | Confirms USDC amount + recipient wallet via Base RPC |
| **Rate limiting** | Per-key Redis counter — configurable per tier |
| **Credit atomicity** | `UPDATE WHERE credits > 0` — eliminates TOCTOU race |
| **Key isolation** | API key never passed to Celery task queue or stored in Redis jobs |
| **Key storage** | SHA-256 hashed — plaintext never in DB |
| **Job status** | `SQLAlchemy Enum` with transition guard — no invalid states possible |
| **Container** | Non-root user (`appuser`), minimal base image |
| **CI scanning** | Bandit + Semgrep + Trivy on every push (actions pinned to verified versions) |
| **Audit log** | Tamper-evident per-request record — PDF exportable from dashboard |
| **Logging** | `structlog` structured JSON throughout — ELK / Loki ready |

### Security Contacts

Responsible disclosure: **ayman@teosegypt.com** · subject: `[SECURITY] safe-ingestion-engine`

Response within 48 hours. Do not open public issues for security vulnerabilities.

---

## Infrastructure Roadmap

### Phase 1 — Core Infrastructure ✅ Complete

- [x] FastAPI + Celery (gevent) + Redis async pipeline
- [x] robots.txt enforcement (structural, not advisory)
- [x] YAML per-domain policy rules + path blocking (wired into PolicyEngine)
- [x] PII pipeline: regex + Presidio NLP (email, phone, SSN, IP, CC, names, passports)
- [x] SSRF protection + DNS rebinding patch + 5MB streaming cap
- [x] x402 USDC payment gate (Base network)
- [x] On-chain transaction verification
- [x] Redis-persisted TX replay protection (90-day TTL)
- [x] SHA-256 API key hashing (plaintext never stored)
- [x] API key isolated from Celery task payload
- [x] Atomic credit deduction (TOCTOU eliminated)
- [x] Job status as SQLAlchemy Enum with transition guard
- [x] Job list endpoint with status filter + pagination
- [x] Streamlit dashboard + PDF audit export
- [x] Docker + healthchecks (worker waits for Redis ready)
- [x] Bandit + Semgrep + Trivy CI (actions pinned)
- [x] `structlog` structured JSON logging throughout
- [x] 22 critical/security/code issues audited and patched

### Phase 2 — Production Infrastructure

- [ ] PostgreSQL backend (async, replaces SQLite)
- [ ] Prometheus `/metrics` endpoint
- [ ] Per-tier rate limiting (configurable per plan)
- [ ] `/health` and `/ready` probes (liveness + readiness)
- [ ] Configurable `robots_error_mode` per domain in YAML

### Phase 3 — Developer Ecosystem

- [ ] Python SDK → PyPI (`pip install safe-ingestion-client`)
- [ ] TypeScript/Node.js SDK
- [ ] CrewAI native `SafeIngestionTool`
- [ ] LangChain native ingestion module
- [ ] Webhook on job completion (`callback_url` param)
- [ ] Test coverage badge + reporting

### Phase 4 — Platform Infrastructure

- [ ] Multi-tenant billing system
- [ ] Usage analytics pipeline
- [ ] Helm chart + Terraform modules
- [ ] Kubernetes HPA by queue depth
- [ ] OpenTelemetry distributed tracing
- [ ] Enterprise deployment templates

---

## Performance Characteristics

| Metric | Characteristic |
|--------|---------------|
| Job submission latency | < 100ms (202 Accepted) |
| Worker concurrency | gevent pool — I/O-bound tasks share greenlets efficiently |
| Worker scalability | Horizontal — add workers independently from API nodes |
| Queue backend | Redis in-memory, sub-millisecond job routing |
| DB writes | Async in worker — does not block API response path |
| Response cap | 5MB streaming per URL |
| PII scan | Regex fast-path first · Presidio deep scan on regex hits |
| Rate limiting | Per-key Redis counter, configurable per tier |

---

## Compliance Alignment

| Framework | Alignment |
|-----------|-----------|
| **GDPR** | Data minimization — PII scrubbed before any persistence |
| **robots.txt standard** | Enforced structurally at policy layer — never advisory, never optional |
| **AI governance** | Full auditable trail for training data provenance |
| **Ethical crawling** | Crawl budgets · delay controls · path blocking · transparent user-agent |
| **Data residency** | SQLite/PostgreSQL under your control — data never leaves your infrastructure |

---

## Use Cases

| Use Case | How Safe Ingestion Helps |
|----------|--------------------------|
| **AI training data** | Compliant, PII-free datasets with full provenance audit |
| **RAG knowledge systems** | robots.txt-safe knowledge base construction at scale |
| **Threat intelligence** | Policy-controlled ingestion with tamper-evident audit trail |
| **Enterprise data pipelines** | GDPR-aligned, governance-enforced web collection |
| **AI agent web access** | x402 autonomous payment — zero human involvement |
| **Security research** | SSRF-safe, rate-limited, fully logged, auditable |

---

## Hosted Platform

A managed deployment is available at **[safe.teosegypt.com](https://safe.teosegypt.com)**

Using the hosted platform grants you licensed access to the API — no separate deployment license needed for API usage.

| Tier | Cost | Credits | Validity |
|------|------|---------|---------|
| Free Trial | $0 | 5 URLs | 48 hours |
| Pay As You Go | $1 minimum | 4 URLs / $1 | Never expires |
| Monthly Starter | $29 / mo | 300 URLs | 30 days |
| Monthly Growth | $79 / mo | 900 URLs | 30 days |
| Yearly Growth | $790 / yr | 9,000 URLs | 365 days |

Payment: USDC on Base · PayPal (`elma7rosa@gmx.com`)

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for setup, code style, and PR process.

By submitting a pull request you assign all intellectual property rights in your contribution to Elmahrosa International, as described in [LICENSE](LICENSE).

**Priority contribution areas:**

| Area | What is needed |
|------|----------------|
| PostgreSQL | Async PostgreSQL backend via `asyncpg` in `core/database.py` |
| Python SDK | Thin client with x402 payment handling → PyPI release |
| CrewAI tool | Native `SafeIngestionTool` class for CrewAI agents |
| LangChain module | Native tool for LangChain chains and agents |
| Webhooks | `callback_url` param → POST on job completion |
| Additional PII | More Presidio entity types: national IDs, tax numbers, IBAN |

---

## License

**Commercial Proprietary License** — see [LICENSE](LICENSE)

Source code is publicly visible for evaluation, security audit, and contribution purposes only. Production and commercial use requires a paid license.

| Use | License required? |
|-----|------------------|
| Local evaluation ≤ 30 days | ✅ Free |
| Non-commercial research ≤ 500 req/mo | ✅ Free |
| Security audit / responsible disclosure | ✅ Free |
| Contributing pull requests | ✅ Free |
| Production deployment (any scale) | 💳 Paid — ayman@teosegypt.com |
| Commercial product / SaaS integration | 💳 Paid — ayman@teosegypt.com |
| Self-hosted enterprise deployment | 💳 Paid — ayman@teosegypt.com |

**Hosted platform** at [safe.teosegypt.com](https://safe.teosegypt.com) grants API access via credits — no separate deployment license required for API usage.

---

## Maintained By

**[Elmahrosa International](https://elmahrosa.com)** — Building sovereign digital infrastructure 🇪🇬

Commercial licensing · security reports · enterprise support: **ayman@teosegypt.com**

---

<div align="center">

**Governance at the pipeline layer. Licensed for production.**

[🌐 Platform](https://safe.teosegypt.com) · [📚 Docs](https://safe.teosegypt.com/docs.html) · [⚡ x402](https://x402.org/ecosystem) · [⭐ Star the repo](https://github.com/Elmahrosa/safe-ingestion-engine)

*Source visible. Security auditable. Production use licensed.*

</div>
