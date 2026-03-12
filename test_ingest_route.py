import hashlib
import os
from pathlib import Path

TEST_API_KEY = "test-api-key"
TEST_API_KEY_HASH = hashlib.sha256(TEST_API_KEY.encode("utf-8")).hexdigest()

os.environ.setdefault("APP_NAME", "safe-ingestion-engine")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("HOST", "0.0.0.0")
os.environ.setdefault("PORT", "8000")
os.environ.setdefault("LOG_LEVEL", "INFO")
os.environ.setdefault("DATABASE_URL", "sqlite:///./data/test_jobs.db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("CELERY_BROKER_URL", "redis://localhost:6379/1")
os.environ.setdefault("CELERY_RESULT_BACKEND", "redis://localhost:6379/2")
os.environ.setdefault("PII_SALT", "0123456789abcdef0123456789abcdef")
os.environ.setdefault("DASHBOARD_ADMIN_PASSWORD", "supersecurepass")
os.environ.setdefault("API_KEY_HASHES_JSON", f'["{TEST_API_KEY_HASH}"]')

Path("./data").mkdir(exist_ok=True)
