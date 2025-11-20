#!/usr/bin/env python3
"""
rag.py — RAG orchestration for local LLM via Ollama.

Features:
 - Retrieves top-k passages (FAISS)
 - Builds context prompt with provenance tags
 - Calls Ollama (7B, 8B, 13B, etc.)
 - Returns: answer, retrieved chunks, prompt, metadata

Requires:
    pip install requests
    ollama installed and running locally
"""

import os
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple

import requests

from src.retriever import semantic_search

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)


# ------------------------------------------------------------------------------------
# LLM wrapper — OLLAMA
# ------------------------------------------------------------------------------------

class OllamaLLM:
    """
    Wrapper around the local Ollama REST API.
    You must have ollama running locally:
        ollama serve
    And a model pulled:
        ollama pull llama3:7b
    """

    def __init__(self, model_name: str = "llama3:7b", url: str = "http://localhost:11434/api/generate"):
        self.model_name = model_name
        self.url = url

    def generate(self, prompt: str, max_tokens: int = 512, temperature: float = 0.0) -> str:
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "temperature": temperature,
            "num_predict": max_tokens,
            "stream": False,
        }

        try:
            resp = requests.post(self.url, json=payload, timeout=120)
            resp.raise_for_status()
        except Exception as e:
            logger.error(f"Ollama request failed: {e}")
            return "Error: LLM generation failed."

        data = resp.json()
        return data.get("response", "").strip()


# ------------------------------------------------------------------------------------
# RAG Core
# ------------------------------------------------------------------------------------

class RAG:
    def __init__(
        self,
        persist_dir: str,
        model_name: str = "llama3:7b",
        sbert_model_name: str = "all-MiniLM-L6-v2",
        top_k: int = 5,
        max_context_chars: int = 3200,
    ):
        """
        persist_dir: FAISS directory created via ingest.py
        model_name: Ollama model name
        sbert_model_name: model for embedding retrieval queries
        top_k: number of passages
        max_context_chars: limit context size to avoid huge prompts
        """
        self.persist_dir = persist_dir
        self.model_name = model_name
        self.top_k = top_k
        self.max_context_chars = max_context_chars
        self.sbert_model_name = sbert_model_name

        # Initialize LLM wrapper
        self.llm = OllamaLLM(model_name=self.model_name)

    # ---------------- Context construction ----------------

    def _build_context(self, retrieved: List[Dict]) -> Tuple[str, List[Dict]]:
        pieces = []
        used = []
        total_chars = 0

        for r in retrieved:
            tag = f"[{r.get('source_name')}#{r.get('chunk_index')}]"
            text = r.get("text") or ""
            block = f"{tag}\n{text}\n"

            if total_chars + len(block) > self.max_context_chars:
                break

            pieces.append(block)
            used.append(r)
            total_chars += len(block)

        context = "\n---\n".join(pieces)
        return context, used

    # ---------------- Prompt ----------------

    def _assemble_prompt(self, query: str, context: str) -> str:
        instructions = (
            "You are a Retrieval-Augmented Generation (RAG) assistant. "
            "Use the provided context passages to answer the question. "
            "Cite sources using their tags (e.g., [doc.pdf#3]). "
            "If the answer is not present in the context, say you don't know."
        )

        prompt = f"""
{instructions}

Context:
{context if context.strip() else "(NO CONTEXT FOUND)"}

Question:
{query}

Answer clearly and cite passages when used.
"""
        return prompt.strip()

    # ---------------- Main RAG entrypoint ----------------

    def answer(
        self,
        query: str,
        top_k: Optional[int] = None,
        temperature: float = 0.0,
        max_tokens: int = 512,
        use_openai_embeddings: bool = False,   # remains compatible but unused for LLM
    ) -> Dict:
        k = top_k or self.top_k

        # Retrieve passages
        retrieved = semantic_search(
            query=query,
            persist_dir=self.persist_dir,
            top_k=k,
            model_name=self.sbert_model_name,
            use_openai=use_openai_embeddings,
        )

        # Build context
        context, used = self._build_context(retrieved)

        # Final prompt
        prompt = self._assemble_prompt(query, context)

        # Generate answer from Ollama
        answer = self.llm.generate(prompt=prompt, max_tokens=max_tokens, temperature=temperature)

        return {
            "query": query,
            "answer": answer,
            "used_documents": used,
            "retrieved": retrieved,
            "prompt": prompt,
        }


# ------------------------------------------------------------------------------------
# CLI
# ------------------------------------------------------------------------------------

def parse_args():
    import argparse
    p = argparse.ArgumentParser(description="Run RAG using local Ollama LLM.")
    p.add_argument("--persist_dir", required=True, help="FAISS index directory")
    p.add_argument("--query", required=True, help="Question to ask")
    p.add_argument("--model", default="llama3:7b", help="Ollama model name")
    p.add_argument("--top_k", type=int, default=5)
    p.add_argument("--temp", type=float, default=0.0)
    p.add_argument("--max_tokens", type=int, default=512)
    return p.parse_args()


def pretty_print(res: Dict):
    print("\n" + "=" * 80)
    print("Query:", res["query"])
    print("\nAnswer:\n", res["answer"])
    print("\n--- Used Documents ---")
    for d in res["used_documents"]:
        print(f"{d.get('source_name')} (chunk {d.get('chunk_index')}) - score={d.get('score'):.4f}")
    print("\n--- Raw Retrieved ---")
    for r in res["retrieved"]:
        print(f"{r['rank']} | {r['score']:.4f} | {r['source_name']} | chunk={r['chunk_index']}")


if __name__ == "__main__":
    args = parse_args()
    rag = RAG(
        persist_dir=args.persist_dir,
        model_name=args.model,
        top_k=args.top_k,
    )
    result = rag.answer(
        query=args.query,
        temperature=args.temp,
        max_tokens=args.max_tokens,
    )
    pretty_print(result)
