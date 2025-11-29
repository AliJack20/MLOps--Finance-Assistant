from fastapi import FastAPI
from pydantic import BaseModel
import joblib
import mlflow
import os
import numpy as np

app = FastAPI(
    title="Milestone1 MLOps API",
    description="FastAPI inference service for MLOps Milestone 1",
    version="1.0.0",
)

# ---------- Models ----------

class Features(BaseModel):
    x1: float
    x2: float
    x3: float


class Prediction(BaseModel):
    prediction: float


# ---------- Load / register model ----------

MODEL_PATH = os.getenv("MODEL_PATH", "src/ml/model.pkl")
_model = None


def load_model():
    global _model
    if _model is None:
        if os.path.exists(MODEL_PATH):
            _model = joblib.load(MODEL_PATH)
        else:
            # fallback tiny dummy model
            from sklearn.linear_model import LinearRegression

            m = LinearRegression()
            m.coef_ = np.array([0.3, 0.5, 0.2])
            m.intercept_ = 0.1
            _model = m
    return _model


@app.on_event("startup")
def startup_event():
    load_model()
    print("✅ Model loaded successfully.")


# ---------- Endpoints ----------

@app.get("/health")
def health():
    """Health-check endpoint for Docker and CI."""
    return {"status": "healthy"}


@app.post("/predict", response_model=Prediction)
def predict(features: Features):
    """Return model prediction for input features."""
    model = load_model()
    data = np.array([[features.x1, features.x2, features.x3]])
    y_pred = model.predict(data)[0]
    return {"prediction": float(y_pred)}


# optional: Prometheus metrics (bonus)
try:
    from prometheus_client import Counter, Histogram, generate_latest
    import time
    from fastapi import Request, Response

    REQUEST_COUNT = Counter("request_count", "App request count", ["method", "endpoint"])
    REQUEST_LATENCY = Histogram("request_latency_seconds", "Request latency", ["endpoint"])

    @app.middleware("http")
    async def metrics_middleware(request: Request, call_next):
        start = time.time()
        response: Response = await call_next(request)
        latency = time.time() - start
        REQUEST_COUNT.labels(request.method, request.url.path).inc()
        REQUEST_LATENCY.labels(request.url.path).observe(latency)
        return response

    @app.get("/metrics")
    def metrics():
        return Response(generate_latest(), media_type="text/plain")

except Exception:
    print("Prometheus metrics not enabled (optional dependency missing)")
