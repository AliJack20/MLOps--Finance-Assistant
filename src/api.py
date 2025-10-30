from fastapi import FastAPI
from src.inference import load_model, predict
import pandas as pd
import instrumentator

app = FastAPI()

model = load_model()


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.post("/predict")
def pred(payload: dict):
    # payload -> pandas DataFrame after preprocessing
    X = pd.DataFrame(payload["instances"])
    preds = predict(model, X)
    return {"predictions": preds}

@app.post("/metrics")
def metrics():
    return generate_latest(instrumentator.metrics())