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
    model = load_model()           # load from S3 inside inference.py
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

        # --- FIX categorical mapping ---
        # Map product_type same way as training
        if "product_type" in df.columns:
            mapping = {"Investment": 1, "OwnerOccupier": 0}
            df["product_type"] = df["product_type"].map(mapping)

        # Drop any non-numeric leftovers
        df = df.select_dtypes(include=["number"])

        # Predict
        preds = model.predict(df)
        return {
            "input": payload,
            "prediction": float(preds[0])
        }

    except Exception as e:
        logger.exception("Prediction failed")
        return {"error": str(e)}
    
    """
    Accepts raw JSON input (flat dict) → runs prediction.
    Example input:
    {
      "full_sq": 89,
      "life_sq": 50,
      "floor": 9,
      "product_type": "Investment"
    }
    """
    try:
        # Convert single JSON input into a DataFrame
        df = pd.DataFrame([payload])
        preds = predict(model, df)
        return {"prediction": float(preds[0])}

    except Exception as e:
        logger.exception("Prediction failed")
        return {"error": str(e)}
@app.get("/metrics")
def metrics():
    """Expose Prometheus metrics endpoint."""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
    