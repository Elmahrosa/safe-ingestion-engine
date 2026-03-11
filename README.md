<div align="center">

<img src="https://raw.githubusercontent.com/Elmahrosa/safe-ingestion-engine/main/logo.png" width="110"/>

# Safe Ingestion Engine

### Compliance-First Infrastructure for Ethical Web Data Ingestion

Policy enforcement · PII protection · SSRF blocking · audit logging · async ingestion

[![Python](https://img.shields.io/badge/Python-3.11-blue?style=flat-square&logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-Production-009688?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=flat-square&logo=docker)](https://docker.com)
[![Security](https://img.shields.io/badge/Security-Safe_by_Design-green?style=flat-square)](#security-model)
[![License](https://img.shields.io/badge/License-Commercial-orange?style=flat-square)](LICENSE)

🌐 Hosted API → https://safe.teosegypt.com  
📄 Documentation → https://safe.teosegypt.com/docs.html

</div>

---

# Overview

Safe Ingestion Engine is a **governed web data ingestion platform** designed for environments where **compliance, traceability, and safety matter as much as speed**.

Most scraping tools optimize for throughput.  
Safe Ingestion Engine optimizes for **responsible ingestion, policy enforcement, and auditability**.

Every request passes through a controlled safety pipeline before a network request is executed.

```

URL Input
│
▼
Policy Engine
robots.txt · domain rules · crawl budgets · SSRF guard
│
▼
Safe Fetch
rate limited · redirect validated · response capped
│
▼
PII Scrubber
email · phone · SSN · IPv4 · credit card
│
▼
Clean Content + Audit Log

```

Blocked requests are **not billed** and remain visible in audit logs.

---

# Key Capabilities

| Capability | Description |
|------------|-------------|
robots.txt compliance | validated before every fetch |
YAML policy rules | allow / deny domain policies |
SSRF protection | blocks private, loopback, metadata IPs |
Redirect validation | redirect chain verified hop-by-hop |
PII scrubbing | email, phone, SSN, IPv4, credit card |
Audit logging | every ingestion decision recorded |
Async ingestion | Celery workers process jobs |
Dashboard | Streamlit metrics and audit export |

---

# Architecture

```

FastAPI Gateway
│
▼
Celery Worker
│
├── Policy Engine
│      robots.txt
│      domain rules
│      crawl budgets
│
├── SafeScraper
│      SSRF guard
│      redirect validation
│      response limits
│
└── PIIScrubber
redact or hash mode

Storage → SQLite
Queue → Redis
Dashboard → Streamlit

```

Stack

```

Python 3.11
FastAPI
Celery
Redis
SQLite
Streamlit
Docker

```

---

# Quick Start (Self-Hosted)

```

git clone [https://github.com/Elmahrosa/safe-ingestion-engine.git](https://github.com/Elmahrosa/safe-ingestion-engine.git)
cd safe-ingestion-engine

cp .env.example .env
make up

```

Services

| Component | URL |
|-----------|-----|
API | http://localhost:8000/docs |
Dashboard | http://localhost:8501 |

---

# Hosted API

A managed version of Safe Ingestion Engine is available at

https://safe.teosegypt.com

The hosted service provides

• managed workers  
• policy-enforced ingestion  
• audit logging  
• usage tracking  
• instant API keys  

---

# Trial Access

New users receive

**5 free URL ingestions**

This trial allows developers to test

• ingestion pipeline  
• PII scrubbing  
• policy enforcement  
• async job system  

Start here

https://safe.teosegypt.com

---

# API Example

Submit ingestion job

```

curl -X POST [http://localhost:8000/v1/ingest_async](http://localhost:8000/v1/ingest_async) 
-H "X-API-Key: YOUR_KEY" 
-H "Content-Type: application/json" 
-d '{"url":"[https://example.com"}](https://example.com%22})'

```

Response

```

{
"job_id": "abc123",
"status": "queued"
}

```

Poll result

```

GET /v1/jobs/{job_id}

```

---

# API Documentation

API documentation is available through

• Swagger UI (`/docs`)  
• exported OpenAPI schema  
• markdown reference docs  

Export OpenAPI

```

curl [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json) -o docs/openapi.json

```

Docs

```

docs/API.md
docs/openapi.json

```

---

# Security Model

| Layer | Control |
|------|---------|
Network | SSRF guard against private networks |
Compliance | robots.txt enforcement |
Policy | domain allow/deny rules |
Fetch | redirect and response limits |
Data | automatic PII scrubbing |
Auth | hashed API keys |
Billing | atomic credit deduction |
Runtime | containerized execution |

Security scans run in CI using

```

Bandit
pip-audit
Trivy

```

---

# Integration Tests

Critical safety logic is validated by integration tests

```

tests/integration/

```

Coverage includes

• policy enforcement  
• robots.txt blocking  
• SSRF protection  
• redirect chain validation  

Run tests

```

pytest tests/integration -v

```

---

# Database Migrations

Schema changes are managed with **Alembic**

```

alembic upgrade head
alembic revision --autogenerate

```

Migration files

```

alembic/versions/

```

---

# Example Data and Policy Packs

Evaluation assets are included

```

examples/datasets/
examples/policies/

```

These contain

• sample URL datasets  
• sanitized ingestion output  
• audit log examples  
• policy templates  

---

# Documentation

| Document | Purpose |
|---------|---------|
ARCHITECTURE.md | system design |
API.md | endpoint reference |
openapi.json | OpenAPI schema |
OPERATIONS.md | runbooks |
SELF_HOSTING.md | deployment guide |
TESTING.md | test strategy |
COMPLIANCE.md | governance |
SECURITY.md | vulnerability reporting |

---

# Roadmap

Planned improvements

• PostgreSQL production backend  
• webhook job completion  
• signed audit exports  
• advanced policy templates  
• enterprise authentication  

---

# Commercial License

This project is **source-available under a commercial license**

Enterprise licensing

```

[license@teosegypt.com](mailto:license@teosegypt.com)

```

See

```

LICENSE

```

---

<div align="center">

Built by **Ayman Seif**  
Elmahrosa International 🇪🇬

</div>
