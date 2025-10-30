"""
Inference API for deployed model.
- Loads trained model from S3 on startup
- Provides /predict and /metrics endpoints
- Exposes Prometheus metrics for API performance
"""

import os
import joblib
import boto3
import logging
import pandas as pd
from fastapi import FastAPI, Request, Response
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

# ----------------------------
# Logging setup
# ----------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ----------------------------
# Environment setup
# ----------------------------
S3_BUCKET = os.getenv("S3_BUCKET")
S3_MODEL_KEY = os.getenv("S3_MODEL_KEY")
AWS_REGION = os.getenv("AWS_REGION")
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")

# ----------------------------
# Prometheus metrics
# ----------------------------
REQUEST_COUNT = Counter("inference_requests_total", "Total inference requests")
RESPONSE_LATENCY = Histogram(
    "inference_latency_seconds", "Inference latency in seconds"
)

# ----------------------------
# Initialize FastAPI app
# ----------------------------
app = FastAPI(title="Finance Assistant Inference API", version="1.0.0")


# ----------------------------
# Helper: download model from S3
# ----------------------------
def download_model_from_s3(
    bucket: str, key: str, local_path: str = "models/latest_model.pkl"
):
    """Download the trained model from S3 to local storage."""
    s3 = boto3.client(
        "s3",
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY,
        region_name=AWS_REGION,
    )
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    logger.info(f"Downloading model from s3://{bucket}/{key}")
    s3.download_file(bucket, key, local_path)
    logger.info(f"Model downloaded to {local_path}")
    return local_path


# ----------------------------
# Load model at startup
# ----------------------------
@app.on_event("startup")
def load_model():
    global model
    model_path = download_model_from_s3(S3_BUCKET, S3_MODEL_KEY)
    model = joblib.load(model_path)
    logger.info("Model loaded successfully.")


# ----------------------------
# Middleware for Prometheus metrics
# ----------------------------
@app.middleware("http")
async def prometheus_middleware(request: Request, call_next):
    REQUEST_COUNT.inc()
    with RESPONSE_LATENCY.time():
        response = await call_next(request)
    return response


# ----------------------------
# Routes
# ----------------------------
@app.get("/")
def home():
    """Health check endpoint."""
    return {"status": "API running", "model_key": S3_MODEL_KEY, "bucket": S3_BUCKET}


@app.post("/predict")
async def predict(data: dict):
    """Perform prediction using loaded model."""
    try:
        X = pd.DataFrame([data])
        preds = model.predict(X)
        return {"prediction": float(preds[0])}
    except Exception as e:
        logger.exception("Prediction failed")
        return {"error": str(e)}


@app.get("/metrics")
def metrics():
    """Expose Prometheus metrics endpoint."""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
