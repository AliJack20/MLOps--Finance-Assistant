# app/huggingface_llm.py
import os
from huggingface_hub import InferenceClient
from typing import Optional, List

HF_TOKEN = os.environ.get("HUGGINGFACEHUB_API_TOKEN")
if not HF_TOKEN:
    raise RuntimeError("Set HUGGINGFACEHUB_API_TOKEN in env")

client = InferenceClient(token=HF_TOKEN)

class HuggingFaceLLM:
    def __init__(self, model_id: str):
        self.model_id = model_id

    def generate(self, prompt: str, max_tokens: int = 512, stop: Optional[List[str]] = None):
        """
        Uses the InferenceClient to call the model.
        If the model supports chat completions, you can use client.chat.completions.create
        or for text generation use client.text_generation.
        """
        # Example using chat completions (if model supports it)
        try:
            # If model has chat endpoint
            resp = client.chat.completions.create(
                model=self.model_id,
                messages=[{"role":"user","content": prompt}],
                max_tokens=max_tokens,
            )
            return resp.choices[0].message["content"]
        except Exception:
            # fallback to text-generation style call
            resp = client.text_generation.create(model=self.model_id, inputs=prompt, max_new_tokens=max_tokens)
            return resp.generated_text
