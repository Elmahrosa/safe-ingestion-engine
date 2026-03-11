# Technical Overview

Safe Ingestion Engine uses a modular architecture designed for safe ingestion workflows.

Core components:

FastAPI Gateway  
Handles authentication, request validation, and job submission.

Celery Worker System  
Executes ingestion jobs asynchronously.

Redis Queue  
Coordinates job scheduling between API and workers.

Policy Engine  
Evaluates ingestion policies before any network request.

Safe Scraper  
Handles controlled HTTP fetching with redirect validation and response limits.

PII Scrubber  
Sanitizes sensitive information before storage.

Audit Logging Layer  
Records every ingestion decision and outcome.

Dashboard Interface  
Streamlit dashboard for monitoring and exporting audit data.

This architecture separates ingestion safety logic from execution logic, improving maintainability and auditability.
