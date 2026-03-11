# System Architecture

Safe Ingestion Engine uses a modular ingestion pipeline designed for safety and auditability.

## Core Components

### API Gateway

FastAPI handles:

• authentication  
• request validation  
• ingestion job creation  
• status polling

Endpoints:

- `/v1/ingest_async`
- `/v1/jobs/{job_id}`
- `/health`

---

### Worker Pipeline

Celery workers execute ingestion jobs asynchronously.

Responsibilities:

• fetch web pages  
• enforce policy checks  
• apply PII scrubbing  
• record audit logs

Workers communicate with the API through Redis queues.

---

### Policy Engine

The policy engine ensures ingestion safety before any network request.

Controls include:

• robots.txt validation  
• domain allow/deny rules  
• crawl budgets  
• rate limits

Policies are defined in:
policies/policy.yml

---

### Safe Scraper

The SafeScraper performs controlled HTTP requests.

Protections include:

• SSRF blocking  
• redirect chain validation  
• response size limits  
• timeout protection

---

### PII Scrubber

Sensitive information is sanitized before storage.

Detected patterns include:

• email addresses  
• phone numbers  
• SSN  
• IPv4 addresses  
• credit card numbers

Scrubbing modes:

• redact
• hash

---

### Storage

Default storage uses SQLite.

Tables include:

• raw_data  
• audit_log  
• request_metrics

Future production deployments may replace SQLite with PostgreSQL.

---

### Dashboard

Streamlit dashboard provides:

• ingestion metrics  
• audit log viewer  
• export functionality
