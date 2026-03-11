# Operations Guide

This document describes operational tasks for Safe Ingestion Engine.

---

## Monitoring

Recommended monitoring:

• API uptime checks
• worker queue size
• ingestion latency
• error rates

---

## Backups

If using SQLite, back up:

```

data/database.db

```

Recommended backup schedule:

daily snapshot

---

## Worker Scaling

Increase ingestion throughput by adding workers.

Example

```

celery -A api.tasks worker --concurrency=4

```

Horizontal scaling is supported.
```
