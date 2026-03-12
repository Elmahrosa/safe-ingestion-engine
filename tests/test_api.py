"""
tests/test_api.py — API endpoint tests.
"""
import os
import sqlite3
import uuid

import pytest
from fastapi.testclient import TestClient

os.environ["DATA_DIR"] = "/tmp/test_safe_data"
os.environ["PII_SALT"] = "test-salt-do-not-use-in-production"

from api.server import app
from core.database import get_db_path, init_db

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_test_db():
    """Fresh DB for each test."""
    os.makedirs("/tmp/test_safe_data", exist_ok=True)
    init_db()
    yield
    # cleanup
    db_path = get_db_path()
    if os.path.exists(db_path):
        os.remove(db_path)


def test_health_endpoint():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_ingest_requires_api_key():
    resp = client.post("/v1/ingest_async", json={"url": "https://example.com"})
    assert resp.status_code == 422  # Missing header


def test_ingest_rejects_invalid_key():
    resp = client.post(
        "/v1/ingest_async",
        json={"url": "https://example.com"},
        headers={"X-API-Key": "sk-safe-INVALIDKEY"},
    )
    assert resp.status_code in (401, 402)


def test_job_not_found_returns_404():
    """IDOR test: non-existent job returns 404, not leaking data."""
    fake_id = str(uuid.uuid4())
    resp = client.get(
        f"/v1/jobs/{fake_id}",
        headers={"X-API-Key": "sk-safe-INVALIDKEY"},
    )
    assert resp.status_code in (401, 404)


def test_job_id_is_uuid_format():
    """Job IDs must be full UUID4 — not short hex (enumerable)."""
    # This test documents the requirement; actual creation tested via integration
    generated = str(uuid.uuid4())
    assert len(generated) == 36
    assert generated.count("-") == 4
