# src/api.py
import os
import logging
from fastapi import FastAPI, Response, HTTPException
from prometheus_fastapi_instrumentator import Instrumentator
import pandas as pd
from pydantic import BaseModel
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

# local imports
from src.inference import load_model, predict  # your existing functions
from src.rag_app.rag import RAG
from src.rag_app.llm import HuggingFaceLLM, call_hf_llm

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(title="Finance Assistant API", version="1.0")

# Initialize Prometheus
instrumentator = Instrumentator().instrument(app)

# Globals (populated at startup)
model = None
rag = None
hf_llm = None


class QueryIn(BaseModel):
    query: str


@app.on_event("startup")
async def startup_event():
    """
    Load model once and expose metrics.
    Also ensure the RAG index is built/loaded and instantiate the HF LLM wrapper.
    """
    global model, rag, hf_llm

    # 1) Load the classical ML model used by /predict
    try:
        model = load_model()  # load from S3 inside inference.py
        logger.info("✅ Prediction model loaded")
    except Exception as e:
        model = None
        logger.exception("Failed loading prediction model at startup")

    # 2) Prepare RAG vectorstore (build if missing)
    try:
        rag = RAG(docs_folder="src/rag_app/data", index_path="src/rag_app/embeddings_cache/faiss_index")
        rag.build_index_if_missing()
        logger.info("✅ RAG index ready")
    except Exception as e:
        rag = None
        logger.exception("Failed to load/build RAG index at startup")

    # 3) Instantiate HuggingFaceLLM wrapper
    try:
        hf_model_id = os.getenv("HF_MODEL_ID", "TheBloke/finance-LLM-AWQ")
        hf_llm = HuggingFaceLLM(model_id=hf_model_id)
        logger.info(f"✅ HuggingFaceLLM initialized (model={hf_model_id})")
    except Exception as e:
        hf_llm = None
        logger.exception("Failed to initialize HuggingFaceLLM at startup")

    # 4) Expose Prometheus metrics (Instrumentator already instrumented app)
    instrumentator.expose(app)
    logger.info("✅ Startup complete and metrics exposed")


@app.post("/qa")
async def qa(q: QueryIn):
    """
    RAG-backed QA endpoint:
      - Uses RAG.query(...) to get both context and a prepared prompt
      - Calls the HuggingFace LLM and returns the answer and the retrieved context
    """
    global rag, hf_llm
    if rag is None:
        raise HTTPException(status_code=503, detail="RAG index not available")

    if hf_llm is None:
        raise HTTPException(status_code=503, detail="LLM not available")

    try:
        res = rag.query(q.query, k=4)
        prompt = res["prompt"]
        context = res["context"]

        # Prefer direct class call, fallback to helper if needed
        try:
            answer = hf_llm.generate(prompt, max_tokens=256)
        except Exception:
            answer = call_hf_llm(prompt, model_id=hf_llm.model_id)

        return {"answer": answer, "context": context}

    except Exception as e:
        logger.exception("QA request failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
def health():
    """Simple health check"""
    return {"status": "healthy"}


@app.post("/predict")
async def predict_api(payload: dict):
    try:
        df = pd.DataFrame([payload])

        if "week" in df.columns:
            df["week"] = pd.to_datetime(df["week"])
            df["week_num"] = df["week"].view("int64") // 10**9

        df = df.select_dtypes(include=["number"])

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
