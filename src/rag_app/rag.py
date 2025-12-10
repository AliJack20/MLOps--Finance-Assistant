# rag.py
import os
import json
import pickle
from typing import List, Optional, Any
from dataclasses import dataclass, field
import inspect

import numpy as np

# Try to import sentence-transformers for good embeddings; otherwise fall back to TF-IDF.
try:
    from sentence_transformers import SentenceTransformer
    _HAS_SENT_TRANS = True
except Exception:
    _HAS_SENT_TRANS = False

# sklearn fallback (TF-IDF + cosine)
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    _HAS_SKLEARN = True
except Exception:
    _HAS_SKLEARN = False

# Optional FAISS support (native)
try:
    import faiss  # type: ignore
    _HAS_FAISS = True
except Exception:
    faiss = None
    _HAS_FAISS = False

# Optional LangChain support
try:
    # Text splitter, loaders, embeddings wrapper, vectorstore, and Document schema
    from langchain.text_splitter import RecursiveCharacterTextSplitter as LCRecursiveCharacterTextSplitter
    from langchain.document_loaders import TextLoader as LCTextLoader
    from langchain.embeddings import HuggingFaceEmbeddings as LCHuggingFaceEmbeddings
    from langchain.vectorstores import FAISS as LCFAISS
    from langchain.schema import Document as LCDocument
    _HAS_LANGCHAIN = True
except Exception:
    LCRecursiveCharacterTextSplitter = None
    LCTextLoader = None
    LCHuggingFaceEmbeddings = None
    LCFAISS = None
    LCDocument = None
    _HAS_LANGCHAIN = False

# ----------------------------
# Small local replacements
# ----------------------------

@dataclass
class Document:
    page_content: str
    metadata: dict = field(default_factory=dict)


class TextLoader:
    """Simple loader that reads a file and returns a list with a single Document."""
    def __init__(self, file_path: str, encoding: str = "utf-8"):
        self.file_path = file_path
        self.encoding = encoding

    def load(self) -> List[Document]:
        with open(self.file_path, "r", encoding=self.encoding, errors="ignore") as f:
            txt = f.read()
        # metadata: source filename
        src = os.path.basename(self.file_path)
        return [Document(page_content=txt, metadata={"source": src})]


class SimpleTextSplitter:
    """
    Lightweight token-agnostic text splitter. Keeps same interface as LangChain's
    RecursiveCharacterTextSplitter for our usage (.split_text).
    """
    def __init__(self, chunk_size: int = 800, chunk_overlap: int = 100):
        self.chunk_size = int(chunk_size)
        self.chunk_overlap = int(chunk_overlap)

    def split_text(self, text: str) -> List[str]:
        if not text:
            return []
        n = self.chunk_size
        o = self.chunk_overlap
        pieces = []
        start = 0
        L = len(text)
        while start < L:
            end = min(start + n, L)
            pieces.append(text[start:end])
            if end == L:
                break
            start = max(0, end - o)
        return pieces


# ----------------------------
# Embeddings wrapper
# ----------------------------
class Embeddings:
    """
    Wrapper that exposes:
      - embed_documents(list[str]) -> np.ndarray (N x D)
      - embed_query(str) -> np.ndarray (D,)
    It tries to use SentenceTransformer (better) or falls back to TF-IDF.
    """
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.model_name = model_name
        self._backend = None  # 'sent' or 'tfidf' or 'langchain' (when using LangChain wrapper)
        self._model = None
        self._tfidf_vectorizer = None
        self._langchain_embeddings = None

        # If LangChain available and its HuggingFaceEmbeddings wrapper exists, prefer it
        if _HAS_LANGCHAIN and LCHuggingFaceEmbeddings is not None:
            try:
                self._langchain_embeddings = LCHuggingFaceEmbeddings(model_name=model_name)
                self._backend = "langchain"
                self._model = None
            except Exception:
                self._langchain_embeddings = None

        if self._langchain_embeddings is None and _HAS_SENT_TRANS:
            try:
                self._model = SentenceTransformer(model_name)
                self._backend = "sent"
            except Exception:
                self._model = None

        if self._model is None and self._langchain_embeddings is None:
            if not _HAS_SKLEARN:
                raise ImportError("No embeddings backend available. Install 'sentence-transformers', 'langchain' or 'scikit-learn'.")
            # TF-IDF fallback (fits on documents later)
            self._backend = "tfidf"
            self._tfidf_vectorizer = TfidfVectorizer(max_features=32768)

    def embed_documents(self, texts: List[str]) -> np.ndarray:
        if self._backend == "langchain":
            # langchain wrapper typically exposes embed_documents
            try:
                emb = self._langchain_embeddings.embed_documents(texts)
                return np.asarray(emb, dtype=np.float32)
            except Exception:
                # fallback to direct behavior
                pass

        if self._backend == "sent":
            emb = self._model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
            return np.asarray(emb, dtype=np.float32)
        else:
            # tfidf: fit_transform
            X = self._tfidf_vectorizer.fit_transform(texts)
            return X.toarray().astype(np.float32)

    def embed_query(self, text: str) -> np.ndarray:
        if self._backend == "langchain":
            try:
                emb = self._langchain_embeddings.embed_query(text)
                return np.asarray(emb, dtype=np.float32)
            except Exception:
                pass

        if self._backend == "sent":
            emb = self._model.encode([text], convert_to_numpy=True, show_progress_bar=False)
            return np.asarray(emb[0], dtype=np.float32)
        else:
            # tfidf: transform (vectorizer must have been fit by embed_documents)
            if self._tfidf_vectorizer is None:
                raise RuntimeError("TF-IDF vectorizer not initialized. Call embed_documents first.")
            v = self._tfidf_vectorizer.transform([text])
            return v.toarray().astype(np.float32)[0]


# ----------------------------
# SimpleVectorStore replacement for FAISS (pure-python)
# ----------------------------
class SimpleVectorStore:
    """
    Minimal vector store providing:
      - from_documents(documents, embeddings)
      - save_local(path)
      - load_local(path, embeddings)
      - similarity_search_by_vector(query_vector, k)
    """
    def __init__(self, documents: List[Document], vectors: np.ndarray):
        self.documents = documents  # list[Document]
        self.vectors = np.asarray(vectors, dtype=np.float32)  # shape (N, D)
        # normalize vectors for cosine similarity convenience
        norms = np.linalg.norm(self.vectors, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        self.normed = self.vectors / norms

    @classmethod
    def from_documents(cls, documents: List[Document], embeddings: Embeddings):
        texts = [d.page_content for d in documents]
        vectors = embeddings.embed_documents(texts)
        return cls(documents=documents, vectors=vectors)

    def save_local(self, path: str):
        """
        Save documents metadata and vectors to the given directory path.
        Creates path if missing. Files:
          - docs.pkl  (list of dicts: {'page_content':..., 'metadata':...})
          - vectors.npy
        """
        os.makedirs(path, exist_ok=True)
        docs_data = [{"page_content": d.page_content, "metadata": d.metadata} for d in self.documents]
        with open(os.path.join(path, "docs.pkl"), "wb") as f:
            pickle.dump(docs_data, f)
        np.save(os.path.join(path, "vectors.npy"), self.vectors)

    @classmethod
    def load_local(cls, path: str, embeddings: Optional[Embeddings] = None):
        """
        Load from path and return a SimpleVectorStore instance.
        'embeddings' is not required for loading, but kept for API compatibility.
        """
        docs_pkl = os.path.join(path, "docs.pkl")
        vecs_npy = os.path.join(path, "vectors.npy")
        if not os.path.exists(docs_pkl) or not os.path.exists(vecs_npy):
            raise FileNotFoundError(f"Index files not found in {path}")
        with open(docs_pkl, "rb") as f:
            docs_data = pickle.load(f)
        documents = [Document(page_content=d["page_content"], metadata=d.get("metadata", {})) for d in docs_data]
        vectors = np.load(vecs_npy)
        return cls(documents=documents, vectors=vectors)

    def similarity_search_by_vector(self, qvec: np.ndarray, k: int = 4) -> List[Document]:
        """
        qvec: (D,) numpy vector (not normalized)
        returns top-k Document objects
        """
        if self.vectors is None or len(self.vectors) == 0:
            return []
        qnorm = np.linalg.norm(qvec)
        if qnorm == 0:
            qnorm = 1.0
        qvec_norm = qvec / qnorm
        sims = np.dot(self.normed, qvec_norm)  # cosine similarity
        topk_idx = np.argsort(-sims)[:k]
        return [self.documents[i] for i in topk_idx if i < len(self.documents)]


# ----------------------------
# FaissVectorStore (optional)
# ----------------------------
class FaissVectorStore:
    """
    Wrapper around faiss index that provides same API as SimpleVectorStore:
      - from_documents(documents, embeddings)
      - save_local(path)
      - load_local(path, embeddings)
      - similarity_search_by_vector(qvec, k)
    """
    def __init__(self, documents: List[Document], vectors: np.ndarray):
        if not _HAS_FAISS:
            raise RuntimeError("faiss is not available")
        self.documents = documents
        self.vectors = np.asarray(vectors, dtype=np.float32)
        # build index with inner product (we'll store normalized vectors for cosine)
        dim = self.vectors.shape[1] if self.vectors.size > 0 else 0
        if dim == 0:
            # empty index
            self.index = faiss.IndexFlatIP(1)
        else:
            self.index = faiss.IndexFlatIP(dim)
        # normalize vectors and add
        norms = np.linalg.norm(self.vectors, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        self.normed = self.vectors / norms
        if self.normed.size > 0:
            self.index.add(self.normed.astype(np.float32))

    @classmethod
    def from_documents(cls, documents: List[Document], embeddings: Embeddings):
        texts = [d.page_content for d in documents]
        vectors = embeddings.embed_documents(texts)
        return cls(documents=documents, vectors=vectors)

    def save_local(self, path: str):
        os.makedirs(path, exist_ok=True)
        # save docs
        docs_data = [{"page_content": d.page_content, "metadata": d.metadata} for d in self.documents]
        with open(os.path.join(path, "docs.pkl"), "wb") as f:
            pickle.dump(docs_data, f)
        # save faiss index
        faiss.write_index(self.index, os.path.join(path, "index.faiss"))

    @classmethod
    def load_local(cls, path: str, embeddings: Optional[Embeddings] = None):
        docs_pkl = os.path.join(path, "docs.pkl")
        index_file = os.path.join(path, "index.faiss")
        if not os.path.exists(docs_pkl) or not os.path.exists(index_file):
            raise FileNotFoundError(f"FAISS index files not found in {path}")
        with open(docs_pkl, "rb") as f:
            docs_data = pickle.load(f)
        documents = [Document(page_content=d["page_content"], metadata=d.get("metadata", {})) for d in docs_data]
        # load faiss index
        index = faiss.read_index(index_file)
        # We don't have the original vectors here; we'll reconstruct a FaissVectorStore with index only.
        # To preserve API we create an instance and attach index & documents.
        inst = object.__new__(cls)
        inst.documents = documents
        inst.index = index
        # fetch dimension from index
        d = int(index.d)
        # We can't get original numeric vectors array easily from faiss index without searching; set vectors empty
        inst.vectors = np.zeros((len(documents), d), dtype=np.float32)
        # Faiss index expects normalized vectors for IP search; we can't reconstruct normed array here — but index contains them
        inst.normed = None  # not used for Faiss search (we query index directly)
        return inst

    def similarity_search_by_vector(self, qvec: np.ndarray, k: int = 4) -> List[Document]:
        if not _HAS_FAISS:
            raise RuntimeError("faiss is not available")
        if self.index.ntotal == 0:
            return []
        # normalize query
        qnorm = np.linalg.norm(qvec)
        if qnorm == 0:
            qnorm = 1.0
        qvec_norm = (qvec / qnorm).astype(np.float32)
        qvec_norm = np.expand_dims(qvec_norm, axis=0)  # shape (1, D)
        distances, indices = self.index.search(qvec_norm, k)  # distances are inner product values
        indices = indices[0].tolist()
        # filter out -1
        results = []
        for idx in indices:
            if idx == -1:
                continue
            if idx < len(self.documents):
                results.append(self.documents[idx])
        return results


# ----------------------------
# RAG class (keeps your API)
# ----------------------------
EMB_MODEL = "sentence-transformers/all-MiniLM-L6-v2"  # kept for backwards compatibility

class RAG:
    def __init__(self,
                 docs_folder: str = "src/rag_app/data",
                 index_path: str = "src/rag_app/embeddings_cache/faiss_index"):
        self.docs_folder = docs_folder
        self.index_path = index_path
        # embeddings wrapper (langchain HuggingFaceEmbeddings if available, else local Embeddings)
        if _HAS_LANGCHAIN and LCHuggingFaceEmbeddings is not None:
            try:
                self.embeddings = LCHuggingFaceEmbeddings(model_name=EMB_MODEL)
                self._emb_backend = "langchain"
            except Exception:
                self.embeddings = Embeddings(model_name=EMB_MODEL)
                self._emb_backend = "local"
        else:
            self.embeddings = Embeddings(model_name=EMB_MODEL)
            self._emb_backend = "local"

        # text splitter replacement (langchain if available)
        if _HAS_LANGCHAIN and LCRecursiveCharacterTextSplitter is not None:
            self.text_splitter = LCRecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
            self._split_backend = "langchain"
        else:
            self.text_splitter = SimpleTextSplitter(chunk_size=800, chunk_overlap=100)
            self._split_backend = "local"

        self.vs: Optional[Any] = None  # can be SimpleVectorStore, FaissVectorStore, or LC FAISS

        if os.path.exists(self.index_path):
            # try to load FAISS index first if faiss is available or langchain FAISS available
            try:
                if _HAS_LANGCHAIN and LCFAISS is not None:
                    # langchain FAISS expects a path with index files created by LCFAISS.save_local
                    try:
                        self.vs = LCFAISS.load_local(self.index_path, self.embeddings)
                    except Exception:
                        self.vs = None
                elif _HAS_FAISS:
                    try:
                        self.vs = FaissVectorStore.load_local(self.index_path, self.embeddings)
                    except Exception:
                        self.vs = None
                else:
                    try:
                        self.vs = SimpleVectorStore.load_local(self.index_path, self.embeddings)
                    except Exception:
                        self.vs = None
            except Exception:
                # if loading fails, leave None so build_index_if_missing can rebuild
                self.vs = None

        # If loaded index exists and we're using TF-IDF backend, ensure TF-IDF vectorizer is refit
        if self.vs is not None and getattr(self.embeddings, "_backend", None) == "tfidf":
            try:
                print("INFO: Refitting TF-IDF vectorizer on loaded documents...")
                # Extract texts from vector store documents (handle LC Documents and local Document)
                texts = []
                for d in getattr(self.vs, "documents", []):
                    if hasattr(d, "page_content"):
                        texts.append(d.page_content)
                    elif isinstance(d, dict):
                        texts.append(d.get("page_content", ""))
                if texts:
                    # this will fit the TF-IDF vectorizer
                    # Note: Embeddings.embed_documents returns np array — we just call it to fit vectorizer
                    if isinstance(self.embeddings, Embeddings):
                        self.embeddings.embed_documents(texts)
                    else:
                        # if langchain embedding wrapper used but ends up with TF-IDF internal, attempt embed_documents
                        try:
                            self.embeddings.embed_documents(texts)
                        except Exception:
                            pass
            except Exception:
                pass

    @staticmethod
    def load_json_file(path: str) -> List[Any]:
        """
        Load a JSON array file where each entry has fields like 'about_me', 'context', 'response'.
        Returns a list of Documents (LangChain Document if LC available, else local Document).
        """
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        docs: List[Any] = []
        for i, entry in enumerate(data):
            combined_text = (
                f"ABOUT ME:\n{entry.get('about_me', '')}\n\n"
                f"FINANCIAL CONTEXT:\n{entry.get('context', '')}\n\n"
                f"ADVICE EXAMPLE:\n{entry.get('response', '')}"
            )
            src_tag = {"source": f"training_case_{i}"}
            if _HAS_LANGCHAIN and LCDocument is not None:
                docs.append(LCDocument(page_content=combined_text, metadata=src_tag))
            else:
                docs.append(Document(page_content=combined_text, metadata=src_tag))
        return docs

    def load_folder_docs(self) -> List[Any]:
        """
        Load docs from self.docs_folder. Accepts:
          - .json files (expected to be an array of training cases)
          - plain text files loaded via TextLoader (LangChain or local)
        Returns list of Documents (LC Document or local Document depending on backend)
        """
        docs: List[Any] = []
        if not os.path.isdir(self.docs_folder):
            return docs

        for fname in os.listdir(self.docs_folder):
            path = os.path.join(self.docs_folder, fname)
            if not os.path.isfile(path):
                continue
            if fname.lower().endswith(".json"):
                try:
                    docs.extend(self.load_json_file(path))
                except Exception:
                    # ignore malformed json files for now
                    continue
            else:
                # use LangChain loader if available
                if _HAS_LANGCHAIN and LCTextLoader is not None:
                    try:
                        loader = LCTextLoader(path, encoding="utf-8")
                        loaded = loader.load()
                        docs.extend(loaded)
                        continue
                    except Exception:
                        # fallback to local loader
                        pass
                loader = TextLoader(path, encoding="utf-8")
                try:
                    docs.extend(loader.load())
                except Exception:
                    continue
        return docs

    def build_index(self):
        """
        Build an index from documents in the folder.
        Splits each document using configured splitter, embeds chunks, and saves a local index.
        """
        docs = self.load_folder_docs()
        if not docs:
            raise RuntimeError(f"No documents found in {self.docs_folder} to build index.")

        # split and create chunked Document objects compatible with chosen vectorstore
        split_docs: List[Any] = []
        for doc in docs:
            content = getattr(doc, "page_content", None) or (doc.get("page_content") if isinstance(doc, dict) else "")
            pieces = self.text_splitter.split_text(content)
            for i, chunk in enumerate(pieces):
                src = {}
                if hasattr(doc, "metadata"):
                    src = doc.metadata
                elif isinstance(doc, dict):
                    src = doc.get("metadata", {})
                # create document in the appropriate type
                if _HAS_LANGCHAIN and LCDocument is not None:
                    split_docs.append(LCDocument(page_content=chunk, metadata={"source": src.get("source", "unknown")}))
                else:
                    split_docs.append(Document(page_content=chunk, metadata={"source": src.get("source", "unknown")}))

        # choose FAISS (LangChain FAISS if available), else local FaissVectorStore, else simple store
        if _HAS_LANGCHAIN and LCFAISS is not None:
            # LangChain FAISS expects langchain Documents and LangChain Embeddings
            # If our embeddings are local wrapper, we can't pass them to LCFAISS; fallback to Simple/Faiss store
            try:
                self.vs = LCFAISS.from_documents(split_docs, self.embeddings)
                os.makedirs(self.index_path, exist_ok=True)
                self.vs.save_local(self.index_path)
                return
            except Exception:
                # fallback to other stores
                pass

        if _HAS_FAISS:
            self.vs = FaissVectorStore.from_documents(split_docs, self.embeddings)
        else:
            self.vs = SimpleVectorStore.from_documents(split_docs, self.embeddings)

        os.makedirs(self.index_path, exist_ok=True)
        # Save local index using whichever store we created
        try:
            self.vs.save_local(self.index_path)
        except Exception:
            # try alternative ways: for LCFAISS it was handled above; otherwise we already implement save_local
            pass

    def build_index_if_missing(self):
        if self.vs is None:
            self.build_index()

    def get_context(self, query: str, k: int = 4) -> str:
        """
        Compute embedding for query, compute cosine similarities against stored vectors,
        and return combined top-k documents as a single string.
        """
        if self.vs is None:
            raise RuntimeError("Index not built. Run build_index() or build_index_if_missing()")

        # compute query vector using the same embeddings backend used to build the index
        # If using LangChain embeddings wrapper, it should implement embed_query/embed_documents
        qvec = None
        try:
            # langchain embeddings object may provide embed_query directly
            qvec = self.embeddings.embed_query(query)
            # ensure numpy array
            qvec = np.asarray(qvec, dtype=np.float32)
        except Exception:
            # if langchain wrapper doesn't have embed_query, fall back to local wrapper behavior
            if isinstance(self.embeddings, Embeddings):
                qvec = self.embeddings.embed_query(query)
            else:
                try:
                    qvec = np.asarray(self.embeddings.embed_documents([query])[0], dtype=np.float32)
                except Exception:
                    raise RuntimeError("Unable to compute query embedding with current embeddings backend.")

        # If using LCFAISS instance, use its similarity search; else use our stores
        top_docs = []
        if _HAS_LANGCHAIN and LCFAISS is not None and isinstance(self.vs, LCFAISS):
            try:
                # LangChain FAISS has similarity_search_by_vector or similarity_search
                if hasattr(self.vs, "similarity_search_by_vector"):
                    top_docs = self.vs.similarity_search_by_vector(qvec, k)
                elif hasattr(self.vs, "similarity_search"):
                    # similarity_search accepts a query string usually; to be safe call similarity_search(query, k=k)
                    top_docs = self.vs.similarity_search(query, k=k)
                else:
                    # fallback to simple search via converting index to python lists if possible
                    top_docs = []
            except Exception:
                top_docs = []
        elif isinstance(self.vs, FaissVectorStore) or (_HAS_FAISS and isinstance(self.vs, FaissVectorStore)):
            top_docs = self.vs.similarity_search_by_vector(qvec, k)
        else:
            top_docs = self.vs.similarity_search_by_vector(qvec, k)

        # Normalize LC documents to have .page_content and .metadata
        normalized = []
        for r in top_docs:
            if hasattr(r, "page_content"):
                normalized.append(r)
            elif isinstance(r, dict):
                normalized.append(Document(page_content=r.get("page_content", ""), metadata=r.get("metadata", {})))
            else:
                # try inspect fields
                content = getattr(r, "page_content", None) or getattr(r, "content", None) or str(r)
                meta = getattr(r, "metadata", {}) or {}
                normalized.append(Document(page_content=content, metadata=meta))

        combined = "\n\n---\n\n".join([
            f"Source: {getattr(r, 'metadata', {}).get('source','unknown')}\nContent: {r.page_content}"
            for r in normalized
        ])
        return combined

    def query(self, query: str, k: int = 4) -> dict:
        """
        Return a dict with keys:
          - 'context': retrieved context string
          - 'prompt': the final prompt to send to the LLM (you can customize template here)
        """
        context = self.get_context(query, k=k)
        # build a safe prompt template: include instructions + context + user query
        prompt = (
            "You are a helpful finance assistant. Use ONLY the information in CONTEXT to answer the question. "
            "If the answer is not contained in the context, say you don't know.\n\n"
            f"CONTEXT:\n{context}\n\n"
            f"QUESTION:\n{query}\n\n"
            "Answer concisely and cite the source tag (e.g., training_case_3) if applicable."
        )
        return {"context": context, "prompt": prompt}
