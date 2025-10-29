from fastapi import FastAPI
from inference import load_model, predict
import pandas as pd
from prometheus_fastapi_instrumentator import Instrumentator
from contextlib import asynccontextmanager

app = FastAPI()

# ✅ Register Prometheus instrumentation BEFORE startup
instrumentator = Instrumentator().instrument(app).expose(app)
model = load_model()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # You could put startup/shutdown logic here if needed
    yield

app.router.lifespan_context = lifespan


@app.get("/health")
def health(): return {"status": "healthy"}

@app.post("/predict")
def pred(payload: dict):
    # payload -> pandas DataFrame after preprocessing
    X = pd.DataFrame(payload["instances"])
    preds = predict(model, X)
    return {"predictions": preds}
