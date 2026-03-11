# Self Hosting Guide

Safe Ingestion Engine can be deployed locally or on private infrastructure.

---

## Requirements

Python 3.11

Docker

Redis

---

## Installation

Clone repository

```

git clone [https://github.com/Elmahrosa/safe-ingestion-engine.git](https://github.com/Elmahrosa/safe-ingestion-engine.git)
cd safe-ingestion-engine

```

Copy environment file

```

cp .env.example .env

```

Start services

```

make up

```

---

## Services

API

```

[http://localhost:8000/docs](http://localhost:8000/docs)

```

Dashboard

```

[http://localhost:8501](http://localhost:8501)

```

---

## Environment Variables

Example configuration

```

PII_MODE=redact
REDIS_URL=redis://redis:6379/0
DATA_DIR=data

```
