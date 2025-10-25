"""
FastAPI application for ML model inference
"""
import time
import logging
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
from prometheus_client import Counter, Histogram, Gauge, generate_latest
from fastapi.responses import Response
import os

# Import model prediction logic
from src.models.predict import ModelPredictor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Prometheus metrics
REQUEST_COUNT = Counter('api_requests_total', 'Total API requests', ['method', 'endpoint', 'status'])
REQUEST_LATENCY = Histogram('api_request_latency_seconds', 'Request latency in seconds', ['endpoint'])
PREDICTION_CONFIDENCE = Gauge('model_prediction_confidence', 'Model prediction confidence')
MODEL_LOAD_TIME = Gauge('model_load_time_seconds', 'Time to load model')

# Global model instance
model_predictor = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load model on startup, cleanup on shutdown"""
    global model_predictor
    logger.info("Loading ML model...")
    start_time = time.time()
    
    try:
        model_predictor = ModelPredictor()
        load_time = time.time() - start_time
        MODEL_LOAD_TIME.set(load_time)
        logger.info(f"Model loaded successfully in {load_time:.2f}s")
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        raise
    
    yield
    
    # Cleanup
    logger.info("Shutting down application...")


# Create FastAPI app
app = FastAPI(
    title="MLOps Sentiment Analysis API",
    description="Production-ready ML inference API with monitoring",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response models
class PredictionRequest(BaseModel):
    """Request schema for predictions"""
    text: str = Field(..., description="Text to analyze", max_length=5000)
    model_version: Optional[str] = Field(None, description="Model version to use")
    
    @validator('text')
    def text_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Text cannot be empty')
        return v.strip()


class PredictionResponse(BaseModel):
    """Response schema for predictions"""
    text: str
    sentiment: str
    confidence: float
    latency_ms: float
    model_version: str


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    model_loaded: bool
    version: str
    environment: str


# Middleware for request tracking
@app.middleware("http")
async def track_requests(request: Request, call_next):
    """Track request metrics"""
    start_time = time.time()
    
    response = await call_next(request)
    
    duration = time.time() - start_time
    REQUEST_LATENCY.labels(endpoint=request.url.path).observe(duration)
    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()
    
    return response


@app.get("/", tags=["General"])
async def root():
    """Root endpoint"""
    return {
        "message": "MLOps Sentiment Analysis API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Health check endpoint for Docker and load balancers"""
    is_canary = os.getenv("CANARY", "false").lower() == "true"
    environment = os.getenv("ENVIRONMENT", "production")
    
    return HealthResponse(
        status="healthy" if model_predictor is not None else "unhealthy",
        model_loaded=model_predictor is not None,
        version="1.0.0",
        environment=f"{environment}{' (canary)' if is_canary else ''}"
    )


@app.post("/predict", response_model=PredictionResponse, tags=["Prediction"])
async def predict_sentiment(request: PredictionRequest):
    """
    Predict sentiment of input text
    
    - **text**: Input text to analyze (max 5000 characters)
    - **model_version**: Optional model version (default: latest)
    
    Returns sentiment (positive/negative/neutral) with confidence score
    """
    if model_predictor is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    try:
        start_time = time.time()
        
        # Get prediction
        result = model_predictor.predict(
            text=request.text,
            model_version=request.model_version
        )
        
        latency = (time.time() - start_time) * 1000  # Convert to milliseconds
        
        # Update metrics
        PREDICTION_CONFIDENCE.set(result['confidence'])
        
        logger.info(f"Prediction: {result['sentiment']} (confidence: {result['confidence']:.3f}, latency: {latency:.2f}ms)")
        
        return PredictionResponse(
            text=request.text,
            sentiment=result['sentiment'],
            confidence=result['confidence'],
            latency_ms=round(latency, 2),
            model_version=result.get('model_version', '1.0')
        )
        
    except Exception as e:
        logger.error(f"Prediction error: {e}")
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")


@app.post("/batch-predict", tags=["Prediction"])
async def batch_predict(texts: list[str]):
    """
    Batch prediction endpoint for multiple texts
    
    - **texts**: List of texts to analyze
    
    Returns list of predictions
    """
    if model_predictor is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    if len(texts) > 100:
        raise HTTPException(status_code=400, detail="Maximum 100 texts per batch")
    
    try:
        results = []
        for text in texts:
            result = model_predictor.predict(text)
            results.append({
                "text": text,
                "sentiment": result['sentiment'],
                "confidence": result['confidence']
            })
        
        return {"predictions": results, "count": len(results)}
        
    except Exception as e:
        logger.error(f"Batch prediction error: {e}")
        raise HTTPException(status_code=500, detail=f"Batch prediction failed: {str(e)}")


@app.get("/metrics", tags=["Monitoring"])
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(content=generate_latest(), media_type="text/plain")


@app.get("/model-info", tags=["Model"])
async def model_info():
    """Get information about the loaded model"""
    if model_predictor is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    return {
        "model_version": "1.0",
        "model_type": "DistilBERT",
        "training_date": "2025-10-20",
        "accuracy": 0.92,
        "f1_score": 0.91,
        "classes": ["negative", "neutral", "positive"]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)