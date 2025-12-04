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
from src.rag_app.guardrails import Guardrails
from src.rag_app.llm import llm_adapter  # the GradioLLM instance
from src.rag_app.rag import RAG

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
guardrails= None


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

        # after hf_llm initialization in startup_event
    try:
        guardrails = Guardrails(embeddings=rag.embeddings if rag is not None else None,
                           tox_threshold=0.3, hallucination_threshold=0.6)
        # attach to module-global so endpoints can access
        globals()["guardrails"] = guardrails
        logger.info("✅ Guardrails initialized")
    except Exception:
        globals()["guardrails"] = None
        logger.exception("Failed to initialize guardrails")

    # 4) Expose metrics
    instrumentator.expose(app)
    logger.info("✅ Startup complete")



@app.post("/qa")
async def qa(q: QueryIn):
    global rag, hf_llm, guardrails

    if rag is None:
        raise HTTPException(status_code=503, detail="RAG index not available")

    if hf_llm is None:
        raise HTTPException(status_code=503, detail="LLM not available")

    # 0. Input validation
    if guardrails is not None:
        ok, details = guardrails.validate_input(q.query)
        if not ok:
            # log event and return 400 (or choose to redact)
            guardrails.log_event("input_violation", {"input": q.query, **details})
            raise HTTPException(status_code=400, detail=f"Input rejected by guardrails: {details['rule']}")

    try:
        res = rag.query(q.query, k=4)
        prompt = res["prompt"]
        context = res["context"]

        answer = await asyncio.to_thread(
            hf_llm.generate,
            prompt,
            "",
            256,
            0.7
        )

        # Output moderation
        if guardrails is not None:
            ok_out, out_details = guardrails.moderate_output(answer, context=context)
            if not ok_out:
                guardrails.log_event("output_violation", {"prompt": prompt, "answer": answer, **out_details})
                # Option 1: redact and return safe message
                redacted = "[The model output was rejected by moderation policies. Please rephrase your query.]"
                return {"answer": redacted, "context": context, "guardrail": out_details}
                # Option 2: raise HTTPException(503, ...) to indicate failure
                # raise HTTPException(status_code=503, detail="Output rejected by guardrails")

        return {"answer": answer, "context": context}

    except Exception:
        logger.exception("QA request failed")
        raise HTTPException(status_code=500, detail="LLM generation failed")




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
