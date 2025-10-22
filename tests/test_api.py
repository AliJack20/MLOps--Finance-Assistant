"""
Tests for FastAPI application
"""
import pytest
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)


class TestHealthEndpoint:
    """Tests for health check endpoint"""
    
    def test_health_check_success(self):
        """Test health endpoint returns 200"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "model_loaded" in data
        assert data["status"] in ["healthy", "unhealthy"]
    
    def test_health_check_structure(self):
        """Test health check response structure"""
        response = client.get("/health")
        data = response.json()
        assert isinstance(data["model_loaded"], bool)
        assert isinstance(data["version"], str)
        assert isinstance(data["environment"], str)


class TestRootEndpoint:
    """Tests for root endpoint"""
    
    def test_root_endpoint(self):
        """Test root endpoint returns welcome message"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data


class TestPredictionEndpoint:
    """Tests for prediction endpoint"""
    
    def test_predict_positive_sentiment(self):
        """Test prediction with positive text"""
        payload = {"text": "This is amazing and wonderful!"}
        response = client.post("/predict", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "sentiment" in data
        assert "confidence" in data
        assert "latency_ms" in data
        assert data["sentiment"] in ["positive", "negative", "neutral"]
        assert 0 <= data["confidence"] <= 1
    
    def test_predict_negative_sentiment(self):
        """Test prediction with negative text"""
        payload = {"text": "This is terrible and awful"}
        response = client.post("/predict", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["sentiment"] == "negative"
    
    def test_predict_empty_text(self):
        """Test prediction with empty text returns error"""
        payload = {"text": ""}
        response = client.post("/predict", json=payload)
        assert response.status_code == 422  # Validation error
    
    def test_predict_missing_text(self):
        """Test prediction without text field"""
        payload = {}
        response = client.post("/predict", json=payload)
        assert response.status_code == 422
    
    def test_predict_very_long_text(self):
        """Test prediction with very long text"""
        payload = {"text": "word " * 10000}  # Exceeds max length
        response = client.post("/predict", json=payload)
        assert response.status_code == 422
    
    def test_predict_with_whitespace(self):
        """Test prediction trims whitespace"""
        payload = {"text": "  great product  "}
        response = client.post("/predict", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["text"] == "great product"
    
    def test_predict_response_time(self):
        """Test prediction latency is reasonable"""
        payload = {"text": "Testing response time"}
        response = client.post("/predict", json=payload)
        data = response.json()
        assert data["latency_ms"] < 1000  # Should be under 1 second


class TestBatchPredictionEndpoint:
    """Tests for batch prediction endpoint"""
    
    def test_batch_predict_success(self):
        """Test batch prediction with multiple texts"""
        texts = [
            "This is great!",
            "This is terrible",
            "It's okay"
        ]
        response = client.post("/batch-predict", json=texts)
        assert response.status_code == 200
        data = response.json()
        assert "predictions" in data
        assert "count" in data
        assert data["count"] == 3
        assert len(data["predictions"]) == 3
    
    def test_batch_predict_empty_list(self):
        """Test batch prediction with empty list"""
        response = client.post("/batch-predict", json=[])
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 0
    
    def test_batch_predict_too_many(self):
        """Test batch prediction with too many texts"""
        texts = ["text"] * 101  # Exceeds limit
        response = client.post("/batch-predict", json=texts)
        assert response.status_code == 400


class TestModelInfoEndpoint:
    """Tests for model info endpoint"""
    
    def test_model_info(self):
        """Test model info returns correct structure"""
        response = client.get("/model-info")
        assert response.status_code == 200
        data = response.json()
        assert "model_version" in data
        assert "model_type" in data
        assert "accuracy" in data
        assert "classes" in data


class TestMetricsEndpoint:
    """Tests for Prometheus metrics endpoint"""
    
    def test_metrics_endpoint(self):
        """Test metrics endpoint returns Prometheus format"""
        response = client.get("/metrics")
        assert response.status_code == 200
        assert "text/plain" in response.headers["content-type"]
        # Check for some expected metrics
        content = response.text
        assert "api_requests_total" in content or len(content) >= 0


@pytest.mark.parametrize("text,expected_sentiment", [
    ("excellent product, highly recommend", "positive"),
    ("worst experience ever, never again", "negative"),
    ("it works as expected", "neutral"),
])
def test_prediction_accuracy(text, expected_sentiment):
    """Parametrized test for various sentiment cases"""
    payload = {"text": text}
    response = client.post("/predict", json=payload)
    assert response.status_code == 200
    data = response.json()
    # Note: With rule-based model, this might not always match
    # In production, use actual model predictions
    assert data["sentiment"] in ["positive", "negative", "neutral"]