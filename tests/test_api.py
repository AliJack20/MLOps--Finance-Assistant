# tests/test_api.py
"""
Test suite for src/api.py
Ensures:
- /health endpoint works
- /predict returns valid response
- Model successfully loads from S3
"""

import json
import pytest
from fastapi.testclient import TestClient
from src.api import app

client = TestClient(app)

# -----------------------------
# Health Endpoint Tests
# -----------------------------

def test_health_endpoint():
    """Verify API health endpoint returns 200 and correct status."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] == "healthy"


# -----------------------------
# Prediction Endpoint Tests
# -----------------------------

@pytest.fixture(scope="module")
def sample_payload():
    """
    Provide a sample input matching model features count.
    The inference.py model uses ExtraTrees trained on n_features_in_ features.
    We can pass a dummy payload of zeros for smoke test.
    """
    # Simple structure expected by POST /predict
    # Replace with your real feature schema if known
    return {"instances": [[0.0] * 10]}  # adjust 10 if you know model.n_features_in_


def test_predict_endpoint_status(sample_payload):
    """Check if /predict returns status 200."""
    response = client.post("/predict", json=sample_payload)
    assert response.status_code == 200


def test_predict_response_structure(sample_payload):
    """Ensure /predict returns a valid predictions list."""
    response = client.post("/predict", json=sample_payload)
    data = response.json()
    assert "predictions" in data, "Response missing 'predictions' key"
    assert isinstance(data["predictions"], list), "Predictions should be a list"


def test_predict_invalid_payload():
    """Ensure /predict gracefully handles invalid or missing data."""
    bad_payload = {"wrong_key": [1, 2, 3]}
    response = client.post("/predict", json=bad_payload)
    assert response.status_code in [400, 422], "Should return validation error for bad input"
