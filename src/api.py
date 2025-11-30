# src/api.py
from fastapi import FastAPI, Response
from prometheus_fastapi_instrumentator import Instrumentator
import pandas as pd
from src.inference import load_model, predict  # use from src.inference
import logging
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(title="Finance Assistant API", version="1.0")

# Initialize Prometheus
instrumentator = Instrumentator().instrument(app)


@app.on_event("startup")
async def startup_event():
    """Load model once and expose metrics"""
    global model
    model = load_model()  # load from S3 inside inference.py
    instrumentator.expose(app)
    logger.info("✅ Model loaded and metrics endpoint exposed")


@app.get("/health")
def health():
    """Simple health check"""
    return {"status": "healthy"}


@app.post("/predict")
async def predict_api(payload: dict):
    try:
        # Convert JSON → DataFrame
        df = pd.DataFrame([payload])

        # --- WEEK PREPROCESSING (match training preprocessing) ---
        if "week" in df.columns:
            # Convert week to datetime if needed
            df["week"] = pd.to_datetime(df["week"], dayfirst=True, errors="coerce")

            # Convert to numeric (timestamp) so model can use it
            df["week"] = df["week"].astype("int64") // 10**9  # seconds

        # Keep only numeric columns for model input
        df = df.select_dtypes(include=["number"])

        # Predict
        preds = model.predict(df)

        return {
            "input": payload,
            "prediction_next_week": float(preds[0])
        }
    
    except Exception as e:
        logger.exception("Prediction failed")
        return {"error": str(e)}
    
    """
    {
    "week": "04/01/2004",
    "actual_spending": 6869.02
    }
    """


@app.get("/metrics")
def metrics():
    """Expose Prometheus metrics endpoint."""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
