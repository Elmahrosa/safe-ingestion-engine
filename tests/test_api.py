from fastapi.testclient import TestClient
from api.server import app
import os

# Mock env for testing
os.environ["DATA_DIR"] = "/tmp/test_data"

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
