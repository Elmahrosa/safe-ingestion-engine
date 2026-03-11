# Deployment Model

Safe Ingestion Engine supports multiple deployment models.

Hosted API

A managed version is available at

https://safe.teosegypt.com

This option requires no infrastructure management.

Private Deployment

Organizations can deploy the system inside their own infrastructure.

Typical components:

FastAPI service  
Celery workers  
Redis queue  
SQLite or PostgreSQL storage

Hybrid Model

A hybrid deployment allows:

• policy enforcement locally
• worker execution remotely
• centralized audit logging

This flexibility allows teams to adapt the system to their security and infrastructure requirements.
