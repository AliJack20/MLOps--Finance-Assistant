# tests/test_health.py
from fastapi.testclient import TestClient
from src.api import app

client = TestClient(app)

def test_health():
    """Ensure that /health endpoint returns 200 and correct JSON."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
