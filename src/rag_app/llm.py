# app/huggingface_llm.py

import os
from typing import Optional, List
from huggingface_hub import InferenceClient

HF_TOKEN = os.environ.get("HUGGINGFACEHUB_API_TOKEN")
if not HF_TOKEN:
    raise RuntimeError("Set HUGGINGFACEHUB_API_TOKEN in env")

client = InferenceClient(token=HF_TOKEN)


class HuggingFaceLLM:
    """
    Wrapper for HF inference API – supports both chat and text-generation models.
    """
    def __init__(self, model_id: str):
        self.model_id = model_id

    def generate(
        self,
        prompt: str,
        max_tokens: int = 512,
        stop: Optional[List[str]] = None
    ) -> str:

        """
        Attempt chat-completions first, fallback to text-generation.
        """

        # Try chat API
        try:
            resp = client.chat.completions.create(
                model=self.model_id,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
            )
            return resp.choices[0].message["content"]

        except Exception:
            # Fallback to text generation
            resp = client.text_generation.create(
                model=self.model_id,
                inputs=prompt,
                max_new_tokens=max_tokens,
            )
            return resp.generated_text


# -------------------------------------------------------------------------
# ❗ This is the function your RAG pipeline will import and call:
# from app.huggingface_llm import call_hf_llm
# -------------------------------------------------------------------------
def call_hf_llm(prompt: str, model_id: str = "TheBloke/finance-LLM-AWQ") -> str:
    """
    Thin wrapper to keep your RAG workflow simple.
    """

    llm = HuggingFaceLLM(model_id=model_id)
    return llm.generate(prompt)
