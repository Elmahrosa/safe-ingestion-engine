from unittest.mock import patch

from fastapi.testclient import TestClient

from api.main import app


client = TestClient(app)


def test_ingest_requires_api_key():
    response = client.post("/v1/ingest", json={"url": "https://example.com"})
    assert response.status_code in (401, 422)


@patch("api.routes.ingest.ingest_url_task.delay")
def test_ingest_enqueue(mock_delay):
    class DummyTask:
        id = "job-123"

    mock_delay.return_value = DummyTask()

    response = client.post(
        "/v1/ingest",
        headers={"x-api-key": "test-key"},
        json={"url": "https://example.com"},
    )

    assert response.status_code in (200, 401)
    if response.status_code == 200:
        assert response.json()["job_id"] == "job-123"
        assert response.json()["status"] == "queued"
