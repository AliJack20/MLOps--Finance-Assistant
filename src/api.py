# src/api.py
from fastapi import FastAPI, Response
from prometheus_fastapi_instrumentator import Instrumentator
import pandas as pd
from src.inference import load_model, predict  # use from src.inference
import logging
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from pydantic import BaseModel
from src.rag_app.rag import RAG
from src.rag_app.llm import HuggingFaceLLM

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(title="Finance Assistant API", version="1.0")

rag = RAG(docs_folder="src/rag_app/data")

if rag.vs is None:
    rag.build_index()

hf_llm = HuggingFaceLLM(model_id="TheBloke/finance-LLM-AWQ")  # replace with your chosen model repo id

class QueryIn(BaseModel):
    query: str

@app.post("/qa")
async def qa(q: QueryIn):
    context = rag.get_context(q.query, k=4)
    prompt = f"""You are an assistant. Use the following context to answer the user's question.\n\nCONTEXT:\n{context}\n\nQuestion: {q.query}\n\nAnswer concisely and cite sources."""
    answer = hf_llm.generate(prompt, max_tokens=256)
    return {"answer": answer}

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
        # Convert JSON → DataFrames
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
        return {"input": payload, "prediction": float(preds[0])}

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