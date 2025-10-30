from fastapi import FastAPI
from src.inference import load_model, predict
import pandas as pd
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI()

model = load_model()

instrumentator = Instrumentator().instrument(app)

@app.on_event("startup")
async def _startup():
    instrumentator.expose(app)

@app.get("/health")
def health():
    return {"status": "healthy"}


@app.post("/predict")
def pred(payload: dict):
    # payload -> pandas DataFrame after preprocessing
    X = pd.DataFrame(payload["instances"])
    preds = predict(model, X)
    return {"predictions": preds}
