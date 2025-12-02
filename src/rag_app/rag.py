# rag.py
import os
import json
from typing import List, Optional
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.document_loaders import TextLoader
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.vectorstores import FAISS
from langchain.schema import Document

EMB_MODEL = "sentence-transformers/all-MiniLM-L6-v2"  # compact, good baseline

class RAG:
    def __init__(self, docs_folder: str = "src/rag_app/data", index_path: str = "src/rag_app/embeddings_cache/faiss_index"):
        self.docs_folder = docs_folder
        self.index_path = index_path
        self.embeddings = HuggingFaceEmbeddings(model_name=EMB_MODEL)
        self.text_splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
        self.vs: Optional[FAISS] = None

        if os.path.exists(self.index_path):
            try:
                self.vs = FAISS.load_local(self.index_path, self.embeddings)
            except Exception:
                # if loading fails, leave None so build_index_if_missing can rebuild
                self.vs = None

    @staticmethod
    def load_json_file(path: str) -> List[Document]:
        """
        Load a JSON array file where each entry has fields like 'about_me', 'context', 'response'.
        Returns a list of LangChain Documents.
        """
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        docs = []
        for i, entry in enumerate(data):
            combined_text = (
                f"ABOUT ME:\n{entry.get('about_me', '')}\n\n"
                f"FINANCIAL CONTEXT:\n{entry.get('context', '')}\n\n"
                f"ADVICE EXAMPLE:\n{entry.get('response', '')}"
            )
            docs.append(Document(page_content=combined_text, metadata={"source": f"training_case_{i}"}))
        return docs

    def load_folder_docs(self) -> List[Document]:
        """
        Load docs from self.docs_folder. Accepts:
          - .json files (expected to be an array of training cases)
          - plain text files loaded via TextLoader
        """
        docs = []
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
                loader = TextLoader(path, encoding="utf-8")
                try:
                    docs.extend(loader.load())
                except Exception:
                    continue
        return docs

    def build_index(self):
        docs = self.load_folder_docs()
        if not docs:
            raise RuntimeError(f"No documents found in {self.docs_folder} to build index.")

        split_docs = []
        for doc in docs:
            pieces = self.text_splitter.split_text(doc.page_content)
            for i, chunk in enumerate(pieces):
                src = doc.metadata.get("source", "unknown")
                split_docs.append(Document(page_content=chunk, metadata={"source": src}))

        self.vs = FAISS.from_documents(split_docs, self.embeddings)
        os.makedirs(self.index_path, exist_ok=True)
        self.vs.save_local(self.index_path)

    def build_index_if_missing(self):
        if self.vs is None:
            self.build_index()

    def get_context(self, query: str, k: int = 4) -> str:
        if self.vs is None:
            raise RuntimeError("Index not built. Run build_index() or build_index_if_missing()")
        results = self.vs.similarity_search(query, k=k)
        combined = "\n\n---\n\n".join([
            f"Source: {getattr(r, 'metadata', {}).get('source','unknown')}\nContent: {r.page_content}"
            for r in results
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
