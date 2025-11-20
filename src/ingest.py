#!/usr/bin/env python3
"""
src/ingest.py

Ingest documents (pdf/txt/md/docx), chunk them, embed chunks, build/persist a FAISS index,
and save chunk metadata.

Requirements:
    pip install -U sentence-transformers faiss-cpu pypdf tqdm python-docx openai

Usage examples:
    # Basic: local sentence-transformers embeddings
    python src/ingest.py --source data/docs --persist_dir db/faiss_db --chunk_size 800 --overlap 150

    # Use OpenAI embeddings (must set OPENAI_API_KEY env var)
    python src/ingest.py --source data/docs --persist_dir db/faiss_db --use_openai
"""
import argparse
import json
import logging
import os
from pathlib import Path
from typing import List, Dict, Tuple
import hashlib

from tqdm import tqdm

# Embedding backends
try:
    from sentence_transformers import SentenceTransformer
except Exception:
    SentenceTransformer = None

# optional: openai embeddings
try:
    import openai
except Exception:
    openai = None

# PDF/text extraction
try:
    from pypdf import PdfReader
except Exception:
    PdfReader = None

try:
    import docx
except Exception:
    docx = None

# FAISS
try:
    import faiss
    import numpy as np
except Exception:
    faiss = None
    np = None

# ---------- Logging ----------
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


# ---------- Utilities ----------
def sha1(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def read_pdf(path: Path) -> str:
    if PdfReader is None:
        raise RuntimeError("pypdf not installed. Install with `pip install pypdf`.")
    reader = PdfReader(str(path))
    pages = []
    for p in range(len(reader.pages)):
        try:
            pages.append(reader.pages[p].extract_text() or "")
        except Exception:
            # fallback safe
            continue
    return "\n".join(pages)


def read_txt(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def read_docx(path: Path) -> str:
    if docx is None:
        raise RuntimeError("python-docx not installed. Install with `pip install python-docx`.")
    doc = docx.Document(str(path))
    paragraphs = [p.text for p in doc.paragraphs]
    return "\n".join(paragraphs)


def extract_text_from_file(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return read_pdf(path)
    if suffix in {".txt", ".md"}:
        return read_txt(path)
    if suffix in {".docx"}:
        return read_docx(path)
    # fallback: try reading as text
    try:
        return read_txt(path)
    except Exception:
        logger.warning("Could not read %s (unsupported).", path)
        return ""


# ---------- Chunking ----------
def chunk_text(text: str, chunk_size: int = 800, overlap: int = 150) -> List[str]:
    """
    Simple chunking based on characters with overlap.
    chunk_size and overlap are in characters (not tokens). This is simple and robust.
    """
    if not text:
        return []
    text = text.replace("\r\n", "\n")
    chunks = []
    start = 0
    text_len = len(text)
    while start < text_len:
        end = start + chunk_size
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= text_len:
            break
        start = end - overlap
        if start < 0:
            start = 0
    return chunks


# ---------- Embedding helpers ----------
class SBERTEmbedder:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        if SentenceTransformer is None:
            raise RuntimeError("sentence-transformers not installed. pip install sentence-transformers")
        logger.info("Loading sentence-transformers model: %s", model_name)
        self.model = SentenceTransformer(model_name)

    def embed(self, texts: List[str]) -> List[List[float]]:
        # returns numpy array
        embs = self.model.encode(texts, show_progress_bar=False, convert_to_numpy=True)
        return embs


class OpenAIEmbedder:
    def __init__(self, model: str = "text-embedding-3-small"):
        if openai is None:
            raise RuntimeError("openai package not installed (pip install openai)")
        if "OPENAI_API_KEY" not in os.environ:
            raise RuntimeError("OPENAI_API_KEY environment variable not set.")
        self.model = model

    def embed(self, texts: List[str]) -> List[List[float]]:
        # Batch requests (simple sequential batching)
        all_embs = []
        for t in tqdm(texts, desc="OpenAI embed", unit="txt"):
            resp = openai.Embedding.create(model=self.model, input=t)
            emb = resp["data"][0]["embedding"]
            all_embs.append(np.array(emb, dtype=np.float32))
        return np.vstack(all_embs)


# ---------- FAISS index helpers ----------
def build_faiss_index(embeddings: np.ndarray) -> faiss.Index:
    """
    Build a FAISS index appropriate for cosine similarity:
    - normalize vectors then use IndexFlatIP (inner product ~ cosine)
    """
    if faiss is None:
        raise RuntimeError("faiss/cpu not installed. pip install faiss-cpu")
    # normalize
    faiss.normalize_L2(embeddings)
    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)  # inner product on normalized vectors == cosine similarity
    index.add(embeddings)
    return index


def save_faiss_index(index: faiss.Index, path: Path):
    faiss.write_index(index, str(path))


def load_faiss_index(path: Path) -> faiss.Index:
    return faiss.read_index(str(path))


# ---------- Main ingest flow ----------
def gather_documents(source: Path) -> List[Path]:
    """
    Recursively find files under source (files only). Filter by supported suffixes.
    """
    supported = {".pdf", ".txt", ".md", ".docx"}
    paths = []
    if source.is_file():
        if source.suffix.lower() in supported:
            return [source]
        else:
            logger.warning("Unsupported file type: %s", source)
            return []
    for p in source.rglob("*"):
        if p.is_file() and p.suffix.lower() in supported:
            paths.append(p)
    return sorted(paths)


def create_metadata_entries(
    source_path: Path, chunks: List[str], doc_id_prefix: str = None
) -> List[Dict]:
    entries = []
    base_name = source_path.name
    doc_hash = sha1(str(source_path.resolve()))
    for i, chunk in enumerate(chunks):
        uid = f"{doc_hash}-{i}"
        entries.append(
            {
                "id": uid,
                "source": str(source_path),
                "source_name": base_name,
                "chunk_index": i,
                "text": chunk,
            }
        )
    return entries


def persist_metadata(metadata: List[Dict], persist_dir: Path):
    meta_path = persist_dir / "metadata.jsonl"
    logger.info("Saving metadata to %s", meta_path)
    with meta_path.open("a", encoding="utf-8") as fh:
        for m in metadata:
            fh.write(json.dumps(m, ensure_ascii=False) + "\n")


def persist_index_and_meta(
    index: faiss.Index, meta: List[Dict], persist_dir: Path, index_name: str = "faiss.index"
):
    persist_dir.mkdir(parents=True, exist_ok=True)
    index_path = persist_dir / index_name
    save_faiss_index(index, index_path)
    # metadata saved as JSONL
    meta_path = persist_dir / "metadata.jsonl"
    logger.info("Writing metadata (%d entries) to %s", len(meta), meta_path)
    with meta_path.open("w", encoding="utf-8") as fh:
        for item in meta:
            fh.write(json.dumps(item, ensure_ascii=False) + "\n")
    logger.info("Index and metadata persisted to %s", persist_dir)


def load_metadata(persist_dir: Path) -> List[Dict]:
    meta_path = persist_dir / "metadata.jsonl"
    if not meta_path.exists():
        return []
    meta = []
    with meta_path.open("r", encoding="utf-8") as fh:
        for line in fh:
            try:
                meta.append(json.loads(line))
            except Exception:
                continue
    return meta


def ingest(
    source: Path,
    persist_dir: Path,
    chunk_size: int = 800,
    overlap: int = 150,
    model_name: str = "all-MiniLM-L6-v2",
    use_openai: bool = False,
    index_name: str = "faiss.index",
):
    paths = gather_documents(source)
    if not paths:
        logger.warning("No documents found under %s", source)
        return

    logger.info("Found %d documents to ingest.", len(paths))

    all_metadata: List[Dict] = []
    all_text_chunks: List[str] = []

    # If existing metadata exists, we can append new docs. Load existing metadata, count items to align with FAISS entries
    existing_meta = []
    if (persist_dir / "metadata.jsonl").exists():
        existing_meta = load_metadata(persist_dir)
        existing_count = len(existing_meta)
        logger.info("Existing metadata found: %d entries. New chunks will be appended.", existing_count)
    else:
        existing_count = 0

    for p in paths:
        logger.info("Reading %s", p)
        txt = extract_text_from_file(p)
        if not txt or txt.strip() == "":
            logger.warning("No text extracted from %s; skipping.", p)
            continue
        chunks = chunk_text(txt, chunk_size=chunk_size, overlap=overlap)
        # create metadata entries
        meta_entries = create_metadata_entries(p, chunks)
        all_metadata.extend(meta_entries)
        all_text_chunks.extend(chunks)

    if not all_text_chunks:
        logger.warning("No text chunks created (empty docs?). Nothing to index.")
        return

    # Embedding
    logger.info("Embedding %d chunks using %s", len(all_text_chunks), "OpenAI" if use_openai else model_name)
    if use_openai:
        if openai is None:
            raise RuntimeError("openai package not installed; install or use sentence-transformers.")
        embedder = OpenAIEmbedder()
    else:
        embedder = SBERTEmbedder(model_name=model_name)

    # get numpy embeddings
    embeddings = embedder.embed(all_text_chunks)
    # convert to numpy float32 if not already
    if not isinstance(embeddings, np.ndarray):
        embeddings = np.array(embeddings, dtype=np.float32)
    else:
        embeddings = embeddings.astype(np.float32)

    # If there's an existing index, we should load and append; otherwise build new
    persist_dir.mkdir(parents=True, exist_ok=True)
    index_path = persist_dir / index_name
    if index_path.exists():
        logger.info("Loading existing FAISS index from %s and appending vectors.", index_path)
        index = load_faiss_index(index_path)
        # ensure normalization
        faiss.normalize_L2(embeddings)
        index.add(embeddings)
        # append metadata (we'll append to metadata.jsonl)
        persist_metadata(all_metadata, persist_dir)
        logger.info("Appended %d vectors to existing index.", embeddings.shape[0])
    else:
        logger.info("Building new FAISS index with %d vectors (dim=%d).", embeddings.shape[0], embeddings.shape[1])
        index = build_faiss_index(embeddings)
        # Persist both
        persist_index_and_meta(index, all_metadata, persist_dir, index_name=index_name)
        logger.info("New index created and persisted.")


# ---------- CLI ----------
def parse_args():
    p = argparse.ArgumentParser(description="Ingest documents and build FAISS index.")
    p.add_argument("--source", type=str, required=True, help="File or folder to ingest")
    p.add_argument("--persist_dir", type=str, required=True, help="Folder to persist FAISS index + metadata")
    p.add_argument("--chunk_size", type=int, default=800, help="Chunk size in characters (default: 800)")
    p.add_argument("--overlap", type=int, default=150, help="Chunk overlap in characters (default: 150)")
    p.add_argument("--model_name", type=str, default="all-MiniLM-L6-v2", help="SBERT model name")
    p.add_argument("--use_openai", action="store_true", help="Use OpenAI embeddings (requires OPENAI_API_KEY)")
    p.add_argument("--index_name", type=str, default="faiss.index", help="Filename for persisted FAISS index")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    src = Path(args.source)
    persist = Path(args.persist_dir)
    ingest(
        source=src,
        persist_dir=persist,
        chunk_size=args.chunk_size,
        overlap=args.overlap,
        model_name=args.model_name,
        use_openai=args.use_openai,
        index_name=args.index_name,
    )
    logger.info("Ingest finished.")
