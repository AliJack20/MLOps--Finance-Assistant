# src/api.py
import os
import logging
from fastapi import FastAPI, Response, HTTPException
from prometheus_fastapi_instrumentator import Instrumentator
import pandas as pd
from pydantic import BaseModel
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
import asyncio
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional, Any

# local imports
from src.inference import load_model, predict  # your existing functions

from src.rag_app.llm import classify_intent, extract_transactions, generate_answer  # the GradioLLM instance
from rag_app.rag import RAG

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(title="Finance Assistant API", version="1.0")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # allow all origins (use specific domains in prod)
    allow_credentials=True,
    allow_methods=["*"],          # allow all HTTP methods
    allow_headers=["*"],          # allow all headers
)

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
    global model, rag, hf_llm

    # 1) Load prediction model
    try:
        model = load_model()
        logger.info("✅ Prediction model loaded")
    except Exception:
        model = None
        logger.exception("Failed loading prediction model at startup")

    # 2) Load/build RAG index
    try:
        rag = RAG(
            docs_folder="src/rag_app/data",
            index_path="src/rag_app/embeddings_cache/faiss_index"
        )
        await asyncio.to_thread(rag.build_index_if_missing)
        logger.info("✅ RAG index ready")
    except Exception:
        rag = None
        logger.exception("Failed to load/build RAG index at startup")

    # 3) Use Gradio LLM Adapter
    try:
        from src.rag_app.llm import llm_adapter
        hf_llm = llm_adapter
        logger.info("✅ Gradio LLM adapter initialized")
    except Exception:
        hf_llm = None
        logger.exception("Failed initializing llm_adapter")

    # 4) Expose metrics
    instrumentator.expose(app)
    logger.info("✅ Startup complete")



# --- Request Models ---
class TextRequest(BaseModel):
    text: str

class AnswerRequest(BaseModel):
    text: str
    data: Optional[List[Any]] = None  # Optional DB records for context

# --- 1. CLASSIFY ENDPOINT (The Router) ---
@app.post("/classify")
async def api_classify(req: TextRequest):
    """
    Node.js calls this first to decide what to do.
    Returns: {"intent": "create" | "query" | "chat", ...}
    """
    try:
        # Run blocking LLM call in a separate thread to keep API async
        result = await asyncio.to_thread(classify_intent, req.text)
        return result
    except Exception as e:
        logger.exception("Classification failed")
        # Fallback to simple chat if brain fails
        return {"intent": "chat", "response": "System error during classification."}

# --- 2. EXTRACT ENDPOINT (The Organizer) ---
@app.post("/extract")
async def api_extract(req: TextRequest):
    """
    Node.js calls this if intent == 'create'.
    Returns: List of JSON transaction objects for the database.
    """
    try:
        result = await asyncio.to_thread(extract_transactions, req.text)
        return result
    except Exception as e:
        logger.exception("Extraction failed")
        return []

# --- 3. ANSWER ENDPOINT (The Speaker) ---
@app.post("/answer")
async def api_answer(req: AnswerRequest):
    """
    Node.js calls this to generate a natural language response.
    - If 'req.data' is sent: It summarizes the DB results (RAG Mode).
    - If 'req.data' is null: It just chats normally (Chat Mode).
    """
    try:
        response_text = await asyncio.to_thread(generate_answer, req.text, req.data)
        return {"response": response_text}
    except Exception as e:
        logger.exception("Answer generation failed")
        return {"response": "I'm having trouble generating a response right now."}


@app.get("/health")
def health():
    """Simple health check"""
    return {"status": "healthy"}


@app.post("/predict")
async def predict_api(payload: dict):
    try:
        print("Received payload:", payload)
        df = pd.DataFrame([payload])
        print("Input DataFrame:", df)
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