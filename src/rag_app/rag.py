# app/rag.py
import os
from typing import List
import json
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.document_loaders import TextLoader  # use other loaders as needed
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.vectorstores import FAISS
from langchain.schema import Document

EMB_MODEL = "sentence-transformers/all-MiniLM-L6-v2"  # compact, good baseline

class RAG:
    def __init__(self, docs_folder: str = "src/rag_app/data", index_path: str = "embeddings_cache/faiss_index"):
        self.docs_folder = docs_folder
        self.index_path = index_path
        self.embeddings = HuggingFaceEmbeddings(model_name=EMB_MODEL)  # LangChain wrapper
        self.text_splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)

        if os.path.exists(index_path):
            # load existing
            self.vs = FAISS.load_local(index_path, self.embeddings)
        else:
            self.vs = None

    def load_json_for_rag(path: str = "src/rag_app/data"):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        docs = []
        for i, entry in enumerate(data):
            combined_text = (
                f"ABOUT ME:\n{entry.get('about_me', '')}\n\n"
                f"FINANCIAL CONTEXT:\n{entry.get('context', '')}\n\n"
                f"ADVICE EXAMPLE:\n{entry.get('response', '')}"
            )
            docs.append(
                Document(
                    page_content=combined_text,
                    metadata={"source": f"training_case_{i}"}
                )
            )
        return docs

    def build_index(self):
        # naive loader for text files; replace with PDF/HTML loaders as needed
        docs = []
        for fname in os.listdir(self.docs_folder):
            path = os.path.join(self.docs_folder, fname)
            if not os.path.isfile(path): 
                continue
            loader = TextLoader(path, encoding="utf-8")
            d = loader.load()
            docs.extend(d)

        # split and embed
        split_docs = []
        for doc in docs:
            pieces = self.text_splitter.split_text(doc.page_content)
            for i, chunk in enumerate(pieces):
                split_docs.append(Document(page_content=chunk, metadata={"source": doc.metadata.get("source", fname)}))

        self.vs = FAISS.from_documents(split_docs, self.embeddings)
        os.makedirs(self.index_path, exist_ok=True)
        self.vs.save_local(self.index_path)

    def get_context(self, query: str, k: int = 4) -> str:
        if self.vs is None:
            raise RuntimeError("Index not built. Run build_index()")

        results = self.vs.similarity_search(query, k=k)
        # combine top docs into a single context string (you may want to add citation markers)
        combined = "\n\n---\n\n".join([f"Source: {getattr(r, 'metadata', {}).get('source','unknown')}\nContent: {r.page_content}" for r in results])
        return combined
