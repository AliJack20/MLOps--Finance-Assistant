#!/usr/bin/env python3
"""
src/retriever.py

Load a persisted FAISS index + metadata (created by src/ingest.py), embed a query,
and return top-k passages.

Requirements:
    pip install -U sentence-transformers faiss-cpu numpy tqdm openai

Usage examples:
    # Basic SBERT local embedder
    python src/retriever.py --persist_dir db/faiss_db --query "What is RAG?" --top_k 5

    # Use OpenAI embeddings
    python src/retriever.py --persist_dir db/faiss_db --query "How to cook pasta?" --use_openai --top_k 3
"""
from pathlib import Path
import json
import logging
from typing import List, Dict, Optional, Tuple

# third-party
try:
    from sentence_transformers import SentenceTransformer
except Exception:
    SentenceTransformer = None

try:
    import openai
except Exception:
    openai = None

try:
    import faiss
    import numpy as np
except Exception:
    faiss = None
    np = None

from tqdm import tqdm

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)


# ---------- Helpers ----------
def load_metadata(persist_dir: Path) -> List[Dict]:
    meta_path = persist_dir / "metadata.jsonl"
    if not meta_path.exists():
        raise FileNotFoundError(f"metadata.jsonl not found in {persist_dir}")
    meta: List[Dict] = []
    with meta_path.open("r", encoding="utf-8") as fh:
        for line in fh:
            try:
                meta.append(json.loads(line))
            except Exception:
                continue
    logger.info("Loaded %d metadata entries.", len(meta))
    return meta


def load_faiss_index(persist_dir: Path, index_name: str = "faiss.index"):
    index_path = persist_dir / index_name
    if not index_path.exists():
        raise FileNotFoundError(f"FAISS index file not found at {index_path}")
    if faiss is None:
        raise RuntimeError("faiss not installed. pip install faiss-cpu")
    index = faiss.read_index(str(index_path))
    logger.info("Loaded FAISS index from %s", index_path)
    return index


# ---------- Embedders ----------
class SBERTEmbedder:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        if SentenceTransformer is None:
            raise RuntimeError("sentence-transformers not installed. pip install sentence-transformers")
        logger.info("Loading SBERT model: %s", model_name)
        self.model = SentenceTransformer(model_name)

    def embed(self, texts: List[str]) -> np.ndarray:
        embs = self.model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
        if not isinstance(embs, np.ndarray):
            embs = np.array(embs, dtype=np.float32)
        return embs.astype(np.float32)


class OpenAIEmbedder:
    def __init__(self, model: str = "text-embedding-3-small"):
        if openai is None:
            raise RuntimeError("openai package not installed. pip install openai")
        if "OPENAI_API_KEY" not in __import__("os").environ:
            raise RuntimeError("OPENAI_API_KEY environment variable not set")
        self.model = model

    def embed(self, texts: List[str]) -> np.ndarray:
        all_embs = []
        for t in tqdm(texts, desc="OpenAI embed", unit="txt"):
            resp = openai.Embedding.create(model=self.model, input=t)
            emb = resp["data"][0]["embedding"]
            all_embs.append(np.array(emb, dtype=np.float32))
        return np.vstack(all_embs)


def normalize_vectors(vectors: np.ndarray) -> np.ndarray:
    """
    L2-normalize rows in-place (returns a copy normalized).
    FAISS inner-product search expects normalized vectors for cosine similarity.
    """
    if vectors is None:
        return vectors
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0.0] = 1e-9
    return vectors / norms


# ---------- Search functions ----------
def semantic_search(
    query: str,
    persist_dir: Path,
    top_k: int = 5,
    model_name: str = "all-MiniLM-L6-v2",
    use_openai: bool = False,
    index_name: str = "faiss.index",
) -> List[Dict]:
    """
    Run a semantic search for a single query. Returns a list of results:
      [{ "rank": 0, "id": "...", "score": 0.92, "text": "...", "source": "...", "chunk_index": 3 }, ...]
    Scores are cosine similarity (because the index uses normalized vectors + IndexFlatIP) in [-1, 1].
    """
    persist_dir = Path(persist_dir)
    index = load_faiss_index(persist_dir, index_name=index_name)
    metadata = load_metadata(persist_dir)

    # embed query
    if use_openai:
        embedder = OpenAIEmbedder()
    else:
        embedder = SBERTEmbedder(model_name=model_name)

    q_emb = embedder.embed([query])
    # ensure float32 numpy array
    q_emb = q_emb.astype(np.float32)
    q_emb = normalize_vectors(q_emb)

    # search FAISS
    if faiss is None:
        raise RuntimeError("faiss not installed.")
    # index.search expects shape (n_queries, dim)
    D, I = index.search(q_emb, top_k)
    # D: distances (inner-product scores), I: indices
    results: List[Dict] = []
    for rank, (score, idx) in enumerate(zip(D[0], I[0])):
        if idx < 0:
            continue
        try:
            meta = metadata[idx]
        except IndexError:
            meta = {"id": None, "source": None, "source_name": None, "chunk_index": None, "text": None}
        results.append(
            {
                "rank": int(rank),
                "id": meta.get("id"),
                "score": float(score),  # cosine similarity in [-1,1]
                "text": meta.get("text"),
                "source": meta.get("source"),
                "source_name": meta.get("source_name"),
                "chunk_index": meta.get("chunk_index"),
            }
        )
    return results


def batch_semantic_search(
    queries: List[str],
    persist_dir: Path,
    top_k: int = 5,
    model_name: str = "all-MiniLM-L6-v2",
    use_openai: bool = False,
    index_name: str = "faiss.index",
) -> List[List[Dict]]:
    """
    Batch search for multiple queries (embeds queries in one shot for SBERT).
    Returns list-of-lists: results per query.
    """
    persist_dir = Path(persist_dir)
    index = load_faiss_index(persist_dir, index_name=index_name)
    metadata = load_metadata(persist_dir)

    if use_openai:
        embedder = OpenAIEmbedder()
    else:
        embedder = SBERTEmbedder(model_name=model_name)

    q_embs = embedder.embed(queries)
    q_embs = q_embs.astype(np.float32)
    q_embs = normalize_vectors(q_embs)

    D, I = index.search(q_embs, top_k)
    all_results: List[List[Dict]] = []
    for qi in range(len(queries)):
        res = []
        for rank, (score, idx) in enumerate(zip(D[qi], I[qi])):
            if idx < 0:
                continue
            try:
                meta = metadata[idx]
            except IndexError:
                meta = {"id": None, "source": None, "source_name": None, "chunk_index": None, "text": None}
            res.append(
                {
                    "rank": int(rank),
                    "id": meta.get("id"),
                    "score": float(score),
                    "text": meta.get("text"),
                    "source": meta.get("source"),
                    "source_name": meta.get("source_name"),
                    "chunk_index": meta.get("chunk_index"),
                }
            )
        all_results.append(res)
    return all_results


# ---------- Simple CLI ----------
def parse_args():
    import argparse

    p = argparse.ArgumentParser(description="Semantic retriever using FAISS index and metadata.")
    p.add_argument("--persist_dir", type=str, required=True, help="Directory containing faiss.index and metadata.jsonl")
    p.add_argument("--query", type=str, help="Single query to run (if omitted, will read from --queries_file)")
    p.add_argument("--queries_file", type=str, help="Path to newline-separated queries file")
    p.add_argument("--top_k", type=int, default=5, help="Top-k results to return")
    p.add_argument("--model_name", type=str, default="all-MiniLM-L6-v2", help="SBERT model name")
    p.add_argument("--use_openai", action="store_true", help="Use OpenAI embeddings (requires OPENAI_API_KEY)")
    p.add_argument("--index_name", type=str, default="faiss.index", help="FAISS index filename")
    return p.parse_args()


def _pretty_print_results(q: str, res: List[Dict]):
    print("\n" + "=" * 80)
    print(f"Query: {q}")
    for r in res:
        print(f"Rank: {r['rank']}\tScore: {r['score']:.4f}\tSource: {r.get('source_name')}\tChunk: {r.get('chunk_index')}")
        snippet = r.get("text") or ""
        print("Snippet:", snippet[:400].replace("\n", " ").strip())
        print("-" * 80)


if __name__ == "__main__":
    args = parse_args()
    persist = Path(args.persist_dir)

    if args.query:
        results = semantic_search(
            query=args.query,
            persist_dir=persist,
            top_k=args.top_k,
            model_name=args.model_name,
            use_openai=args.use_openai,
            index_name=args.index_name,
        )
        _pretty_print_results(args.query, results)
    elif args.queries_file:
        qfile = Path(args.queries_file)
        queries = [l.strip() for l in qfile.read_text(encoding="utf-8").splitlines() if l.strip()]
        all_results = batch_semantic_search(
            queries=queries,
            persist_dir=persist,
            top_k=args.top_k,
            model_name=args.model_name,
            use_openai=args.use_openai,
            index_name=args.index_name,
        )
        for q, res in zip(queries, all_results):
            _pretty_print_results(q, res)
    else:
        print("Provide --query 'your question' or --queries_file path.txt")
