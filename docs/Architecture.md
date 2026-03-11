
# System Architecture

Safe Ingestion Engine uses a modular ingestion pipeline designed for safety, compliance, and auditability.

## System Diagram

```mermaid
flowchart TD
    A[Client] --> B[FastAPI API]
    B --> C[Redis Queue]
    C --> D[Celery Workers]
    D --> E[Policy Engine]
    E --> F[Safe Scraper]
    F --> G[PII Scrubber]
    G --> H[Database]
    H --> I[Dashboard]
````

The diagram shows the end-to-end data flow through the main system components:

```text
Client
  ↓
FastAPI API
  ↓
Redis Queue
  ↓
Celery Workers
  ↓
Policy Engine
  ↓
Safe Scraper
  ↓
PII Scrubber
  ↓
Database
  ↓
Dashboard
```

## Core Components

### API Gateway

FastAPI handles:

* authentication
* request validation
* ingestion job creation
* status polling

Main endpoints:

* `/v1/ingest_async`
* `/v1/jobs/{job_id}`
* `/health`

### Worker Pipeline

Celery workers execute ingestion jobs asynchronously.

Responsibilities:

* fetch web pages
* enforce policy checks
* apply PII scrubbing
* record audit logs

Workers communicate with the API through Redis queues.

### Policy Engine

The policy engine ensures ingestion safety before any network request is made.

Controls include:

* robots.txt validation
* domain allow and deny rules
* crawl budgets
* rate limits

Policies are defined in:

`policies/policy.yml`

### Safe Scraper

The Safe Scraper performs controlled HTTP requests.

Protections include:

* SSRF blocking
* redirect chain validation
* response size limits
* timeout protection

### PII Scrubber

Sensitive information is sanitized before storage.

Detected patterns include:

* email addresses
* phone numbers
* SSNs
* IPv4 addresses
* credit card numbers

Scrubbing modes:

* `redact`
* `hash`

### Storage

Default storage uses SQLite.

Tables include:

* `raw_data`
* `audit_log`
* `request_metrics`

For production deployments, SQLite can be replaced with PostgreSQL.

### Dashboard

The Streamlit dashboard provides:

* ingestion metrics
* audit log viewer
* export functionality

```
