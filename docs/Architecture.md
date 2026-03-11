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
