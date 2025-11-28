# src/api.py
from fastapi import FastAPI, Response, UploadFile, File, HTTPException, Body
from prometheus_fastapi_instrumentator import Instrumentator
import pandas as pd
import os
import shutil
import json
import logging
from pathlib import Path
from typing import List, Optional
import uvicorn

from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

# existing inference imports (your finance model)
from src.inference import load_model, predict  # ensure src/inference.py exposes these

# RAG / retrieval imports
from src.ingest import ingest as ingest_fn
from src.retriever import semantic_search
from src.rag import RAG

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(title="Finance + RAG API", version="1.1")

# Initialize Prometheus Instrumentator
instrumentator = Instrumentator().instrument(app)

# Configuration via env vars (defaults)
PERSIST_DIR = Path(os.environ.get("RAG_PERSIST_DIR", "db/faiss_db"))
SBERT_MODEL = os.environ.get("SBERT_MODEL", "all-MiniLM-L6-v2")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3:7b")
DEFAULT_TOP_K = int(os.environ.get("RAG_TOP_K", "5"))

# Ensure persist dir exists
PERSIST_DIR.mkdir(parents=True, exist_ok=True)

# Global placeholders - will be set at startup
model = None         # finance model loaded from src.inference
rag_instance = None  # RAG instance


# -----------------------
# Startup
# -----------------------
@app.on_event("startup")
async def startup_event():
    """
    Load finance model and instantiate RAG instance.
    Also expose Prometheus metrics.
    """
    global model, rag_instance
    # Load finance model (may download from S3 inside load_model)
    model = load_model()
    logger.info("✅ Finance model loaded")

    # Expose instrumentator metrics endpoints (instrumentator already instrumented app above)
    instrumentator.expose(app)
    logger.info("✅ Prometheus instrumentator exposed")

    # Create RAG instance (re-usable)
    rag_instance = RAG(
        persist_dir=str(PERSIST_DIR),
        model_name=OLLAMA_MODEL,
        sbert_model_name=SBERT_MODEL,
        top_k=DEFAULT_TOP_K,
    )
    logger.info("✅ RAG instance created (model=%s, sbert=%s)", OLLAMA_MODEL, SBERT_MODEL)


# -----------------------
# Utilities
# -----------------------
def save_upload_file(tmp_dir: Path, upload_file: UploadFile) -> Path:
    """
    Save uploaded file to tmp_dir and return its path.
    """
    tmp_dir.mkdir(parents=True, exist_ok=True)
    dest = tmp_dir / upload_file.filename
    with dest.open("wb") as fh:
        shutil.copyfileobj(upload_file.file, fh)
    return dest


def read_metadata_head(persist_dir: Path, n: int = 100):
    meta_path = persist_dir / "metadata.jsonl"
    if not meta_path.exists():
        return []
    out = []
    with meta_path.open("r", encoding="utf-8") as fh:
        for i, line in enumerate(fh):
            if i >= n:
                break
            try:
                out.append(json.loads(line))
            except Exception:
                continue
    return out


# -----------------------
# Health / metrics
# -----------------------
@app.get("/health")
def health():
    """Simple health check"""
    try:
        test_path = PERSIST_DIR / ".health_check"
        test_path.write_text("ok")
        test_path.unlink(missing_ok=True)
    except Exception as e:
        logger.exception("Health check failed: %s", e)
        raise HTTPException(status_code=500, detail="Persist dir not writable or missing.")
    return {"status": "healthy", "persist_dir": str(PERSIST_DIR)}


@app.get("/metrics")
def metrics():
    """Expose Prometheus metrics endpoint."""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


# -----------------------
# Prediction endpoint (Finance)
# -----------------------
@app.post("/predict")
async def predict_api(payload: dict):
    """
    Accepts raw JSON input (flat dict) → runs prediction using the loaded finance model.
    Example input:
    {
      "full_sq": 89,
      "life_sq": 50,
      "floor": 9,
      "product_type": "Investment"
    }
    """
    global model
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    try:
        # Convert single JSON input into a DataFrame
        df = pd.DataFrame([payload])

        # --- FIX categorical mapping (same mapping used during training) ---
        if "product_type" in df.columns:
            mapping = {"Investment": 1, "OwnerOccupier": 0}
            df["product_type"] = df["product_type"].map(mapping)

        # Drop non-numeric columns (the model expects numeric features)
        df = df.select_dtypes(include=["number"])

        # If you have a wrapper predict(model, df) use it; otherwise fallback to model.predict
        try:
            preds = predict(model, df)
        except Exception:
            preds = model.predict(df)

        return {"input": payload, "prediction": float(preds[0])}

    except Exception as e:
        logger.exception("Prediction failed")
        raise HTTPException(status_code=500, detail=str(e))


# -----------------------
# Ingest endpoints (synchronous)
# -----------------------
@app.post("/ingest")
def ingest(files: List[UploadFile] = File(...), chunk_size: int = 800, overlap: int = 150, model_name: str = SBERT_MODEL):
    """
    Accept multiple file uploads and immediately ingest them into the FAISS index stored under PERSIST_DIR.
    This endpoint saves files into a temporary folder under PERSIST_DIR/uploads and calls ingest_fn synchronously.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")

    upload_dir = PERSIST_DIR / "uploads" / f"batch_{os.getpid()}"
    upload_dir.mkdir(parents=True, exist_ok=True)
    saved_paths = []
    try:
        for f in files:
            saved = save_upload_file(upload_dir, f)
            saved_paths.append(str(saved))

        # Call ingest function for the upload_dir
        ingest_fn(
            source=upload_dir,
            persist_dir=PERSIST_DIR,
            chunk_size=chunk_size,
            overlap=overlap,
            model_name=model_name,
            use_openai=False,
        )

        return {"success": True, "message": "Files ingested successfully.", "ingested_files": saved_paths}
    except Exception as e:
        logger.exception("Ingest failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Ingest failed: {e}")


@app.post("/ingest_from_path")
def ingest_from_path(path: str = Body(..., embed=True), chunk_size: int = 800, overlap: int = 150, model_name: str = SBERT_MODEL):
    """
    Ingest files that already exist on the local filesystem (path can be a file or a folder).
    Useful for server-side staged data (S3-mounted folders, etc.). Runs synchronously.
    """
    p = Path(path)
    if not p.exists():
        raise HTTPException(status_code=400, detail=f"Path does not exist: {path}")

    try:
        ingest_fn(
            source=p,
            persist_dir=PERSIST_DIR,
            chunk_size=chunk_size,
            overlap=overlap,
            model_name=model_name,
            use_openai=False,
        )
        return {"success": True, "message": f"Ingested files from {path}", "ingested_path": str(p)}
    except Exception as e:
        logger.exception("ingest_from_path failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Ingest failed: {e}")


# -----------------------
# Retrieval endpoint (semantic search only)
# -----------------------
@app.post("/retrieve")
def retrieve(body: dict = Body(...)):
    """
    Body example:
    {
        "query": "What is RAG?",
        "top_k": 5,
        "model_name": "all-MiniLM-L6-v2",
        "use_openai_embeddings": false
    }
    """
    query = body.get("query")
    if not query:
        raise HTTPException(status_code=400, detail="Missing 'query' in request body")
    top_k = int(body.get("top_k", DEFAULT_TOP_K))
    model_name = body.get("model_name", SBERT_MODEL)
    use_openai_embeddings = bool(body.get("use_openai_embeddings", False))

    try:
        results = semantic_search(
            query=query,
            persist_dir=PERSIST_DIR,
            top_k=top_k,
            model_name=model_name,
            use_openai=use_openai_embeddings,
        )
        return {"query": query, "top_k": top_k, "results": results}
    except Exception as e:
        logger.exception("Retrieval failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Retrieval failed: {e}")


# -----------------------
# RAG / Query endpoint (retrieval + Ollama generation)
# -----------------------
@app.post("/query")
def query(body: dict = Body(...)):
    """
    Body example:
    {
        "query": "Explain the refund policy",
        "top_k": 5,
        "temperature": 0.0,
        "max_tokens": 512,
        "use_openai_embeddings": false
    }
    """
    global rag_instance
    if rag_instance is None:
        raise HTTPException(status_code=503, detail="RAG instance not initialized")

    query_text = body.get("query")
    if not query_text:
        raise HTTPException(status_code=400, detail="Missing 'query' in request body")

    top_k = int(body.get("top_k", rag_instance.top_k))
    temperature = float(body.get("temperature", 0.0))
    max_tokens = int(body.get("max_tokens", 512))
    use_openai_embeddings = bool(body.get("use_openai_embeddings", False))

    try:
        # create a local RAG with desired top_k to avoid mutating the global instance
        local_rag = RAG(
            persist_dir=str(PERSIST_DIR),
            model_name=rag_instance.model_name,
            sbert_model_name=rag_instance.sbert_model_name,
            top_k=top_k,
            max_context_chars=getattr(rag_instance, "max_context_chars", 3200),
        )

        res = local_rag.answer(
            query=query_text,
            top_k=top_k,
            temperature=temperature,
            max_tokens=max_tokens,
            use_openai_embeddings=use_openai_embeddings,
        )

        return {
            "query": res.get("query"),
            "answer": res.get("answer"),
            "used_documents": res.get("used_documents", []),
            "retrieved": res.get("retrieved", []),
            "prompt": res.get("prompt"),
        }
    except Exception as e:
        logger.exception("RAG query failed: %s", e)
        raise HTTPException(status_code=500, detail=f"RAG query failed: {e}")


# -----------------------
# Metadata & admin endpoints
# -----------------------
@app.get("/metadata")
def metadata(limit: int = 100):
    """
    Return first `limit` entries from metadata.jsonl for inspection.
    """
    try:
        data = read_metadata_head(PERSIST_DIR, n=limit)
        return {"count": len(data), "items": data}
    except Exception as e:
        logger.exception("metadata read failed: %s", e)
        raise HTTPException(status_code=500, detail=f"metadata read failed: {e}")


@app.post("/reload_rag")
def reload_rag():
    """
    Re-create the global rag_instance (useful if you've updated the index and want a fresh object).
    """
    global rag_instance
    try:
        rag_instance = RAG(
            persist_dir=str(PERSIST_DIR),
            model_name=OLLAMA_MODEL,
            sbert_model_name=SBERT_MODEL,
            top_k=DEFAULT_TOP_K,
        )
        return {"status": "reloaded", "model": rag_instance.model_name}
    except Exception as e:
        logger.exception("reload_rag failed: %s", e)
        raise HTTPException(status_code=500, detail=f"reload_rag failed: {e}")
    


class QARequest(BaseModel):
    question: str
    top_k: int = 4

@app.post("/qa")
async def qa(req: QARequest):
    # use chain from rag_service
    res = chain.run({"query": req.question})
    # optionally return raw retrieved docs and metadata
    return {"answer": res}

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000)
