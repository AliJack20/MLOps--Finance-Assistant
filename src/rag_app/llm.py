# llm.py
import os
import json
from dotenv import load_dotenv
from gradio_client import Client

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

HF_TOKEN = os.getenv("HF_TOKEN", None)
HF_SPACE = os.getenv("HF_SPACE", "MuhammadHamza33/mistral-7b-test")  # space identifier

if HF_TOKEN is None:
    # You may prefer to raise here. For now, we log and continue (Client can work without token for public spaces)
    print("Warning: HF_TOKEN not set. If your Space requires authentication, set HF_TOKEN in .env")

# Create a gradio client for the Space
client = Client(HF_SPACE, token=HF_TOKEN)


class GradioLLM:
    """
    Adapter around gradio_client.Client to expose a generate(prompt, max_tokens, temperature)
    method compatible with your api.py usage (hf_llm.generate(...)) and .model_id attribute.
    """

    def __init__(self, client: Client, model_id: str = None, api_name: str = "/generate"):
        self.client = client
        self.api_name = api_name
        self.model_id = model_id or HF_SPACE

    def generate(self, prompt: str, max_tokens: int = 256, temperature: float = 0.7) -> str:
        """
        Calls the Space /generate (or configured api_name) endpoint.
        Adjust args depending on the Space's signature.
        Returns plain text.
        """
        # Many Spaces accept (prompt, max_new_tokens, temperature) or (input, ...).
        # Adapt here depending on your space's function signature.
        try:
            # Try a common signature: (input, system_prompt, max_tokens, temperature) like you used.
            out = self.client.predict(
                prompt,
                "",                # leaving system message blank (you can set if needed)
                max_tokens,
                temperature,
                api_name=self.api_name
            )
        except TypeError:
            # fallback: try single-argument 'prompt'
            out = self.client.predict(prompt, api_name=self.api_name)
        # Some Spaces return a list or dict - normalize to string
        if isinstance(out, (list, tuple)):
            try:
                return out[0]
            except Exception:
                return json.dumps(out)
        if isinstance(out, dict):
            # If the space returns a dict like {"generated_text": "..."}
            if "generated_text" in out:
                return out["generated_text"]
            # Convert dict to JSON string as fallback
            return json.dumps(out)
        return str(out)


# simple helpers that use the adapter
llm_adapter = GradioLLM(client=client, model_id=HF_SPACE)


def get_intent(user_text: str):
    detective_prompt = """
You are a precise data classifier.
Extract the 'search_term' from the user's request as JSON.
Example: "How much on food?" -> {"search_term": "Food"}
Output ONLY JSON.
"""
    # Use low temperature for deterministic extraction
    return llm_adapter.generate(f"{user_text}\n\n{detective_prompt}", max_tokens=100, temperature=0.1)


def get_answer(user_text: str, data_context: str):
    advisor_prompt = f"""
You are FinBot, a friendly financial assistant.
Use the provided data to answer the user.

DATA CONTEXT:
{data_context}
"""
    return llm_adapter.generate(f"{user_text}\n\n{advisor_prompt}", max_tokens=200, temperature=0.4)


# --- TEST FLOW (only run when module executed directly) ---
if __name__ == "__main__":
    user_input = "How much did I spend on burgers?"
    intent_json = get_intent(user_input)
    print("Detected Intent:", intent_json)
    final_response = get_answer(user_input, "User spent $15.00 on Burger King.")
    print("Bot Answer:", final_response)
