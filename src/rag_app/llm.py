import os
import json
import re
from dotenv import load_dotenv
from gradio_client import Client

# Load environment variables
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

HF_TOKEN = os.getenv("HF_TOKEN", None)
HF_SPACE = os.getenv("HF_SPACE", "MuhammadHamza33/mistral-7b-test")  # space identifier

if HF_TOKEN is None:
    print("Warning: HF_TOKEN not set. If your Space requires authentication, set HF_TOKEN in .env")

# Create a gradio client for the Space
client = Client(HF_SPACE, token=HF_TOKEN)

class GradioLLM:
    """
    Adapter around gradio_client.Client to expose a generate method.
    """
    def __init__(self, client: Client, model_id: str = None, api_name: str = "/generate"):
        self.client = client
        self.api_name = api_name
        self.model_id = model_id or HF_SPACE

    def generate(self, prompt: str, max_tokens: int = 512, temperature: float = 0.1) -> str:
        try:
            out = self.client.predict(
                prompt,
                "", # System prompt left blank
                max_tokens,
                temperature,
                api_name=self.api_name
            )
        except TypeError:
            # Fallback for different API signatures
            out = self.client.predict(prompt, api_name=self.api_name)
        
        # Handle different return types
        if isinstance(out, (list, tuple)):
            try: return out[0]
            except: return str(out)
        if isinstance(out, dict) and "generated_text" in out:
            return out["generated_text"]
        return str(out)

# Initialize the adapter
llm_adapter = GradioLLM(client=client, model_id=HF_SPACE)

# --- 🔥 IMPROVED CLEANER ---
def clean_json_output(raw_text: str):
    print(f"\n--- DEBUG: RAW LLM OUTPUT ---\n{raw_text}\n-----------------------------\n")
    
    # 1. Try finding a JSON Code Block (```json ... ```)
    match = re.search(r"```json\s*([\s\S]*?)\s*```", raw_text)
    if match:
        raw_text = match.group(1)

    # 2. Try finding the outermost list [...] or object {...}
    try:
        # Look for [ ... ] first (Priority for extraction)
        list_match = re.search(r"(\[.*\])", raw_text, re.DOTALL)
        if list_match:
            return json.loads(list_match.group(1))
            
        # Look for { ... } next (Priority for intent)
        obj_match = re.search(r"(\{.*\})", raw_text, re.DOTALL)
        if obj_match:
            return json.loads(obj_match.group(1))
            
    except json.JSONDecodeError as e:
        print(f"❌ JSON Parse Error: {e}")
        # Last ditch: try to fix single quotes to double quotes
        try:
            fixed_text = raw_text.replace("'", '"')
            if list_match: return json.loads(re.search(r"(\[.*\])", fixed_text, re.DOTALL).group(1))
            if obj_match: return json.loads(re.search(r"(\{.*\})", fixed_text, re.DOTALL).group(1))
        except:
            pass

    return None
# ==========================================
# 🧠 MODE 1: INTENT CLASSIFIER (Refined)
# ==========================================
def classify_intent(user_text: str):
    """
    Decides the action and extracts high-level filters for queries.
    """
    prompt = f"""
    You are a financial AI router. Analyze the user's request and output strict JSON.
    
    MODES:
    1. "create": User wants to add/spend/earn money. (Do NOT extract details here, just return intent).
    2. "query": User asks for data. Extract precise filters: 'category', 'time_range' (e.g., 'this month', 'today', '2024'), 'type' (income/expense).
    3. "chat": General greetings or non-financial questions.

    EXAMPLES:
    
    Input: "I spent $15 on coffee and $200 on groceries"
    JSON: {{ "intent": "create" }}  <-- Clean output for creation

    Input: "How much have I spent on food this month?"
    JSON: {{ "intent": "query", "filters": {{ "category": "Food", "time_range": "this month" }} }}

    Input: "Show me my income from last year"
    JSON: {{ "intent": "query", "filters": {{ "type": "income", "time_range": "last year" }} }}

    Input: "Hi, who are you?"
    JSON: {{ "intent": "chat" }}

    Input: "{user_text}"
    JSON:
    """
    response = llm_adapter.generate(prompt, max_tokens=150, temperature=0.1)
    return clean_json_output(response) or {"intent": "chat"}
# ==========================================
# 📝 MODE 2: BULK EXTRACTOR (The Organiser)
# ==========================================
# ==========================================
# 📝 MODE 2: EXTRACTOR (Unchanged)
# ==========================================
def extract_transactions(user_text: str):
    prompt = f"""
    Extract financial records from text into a JSON LIST.
    Fields: title, amount (number), type (income/expense), category, date (YYYY-MM-DD or 'today').
    RULES:
    - Amounts should be numbers only (no $ sign).
    - Type is 'income' if money is received, 'expense' if money is spent.
    - Date should be 'today' if no specific date is mentioned.
    -Number should always be positive.
    Input: "Spent $20 on KFC and $50 on Gas today"
    JSON: [
        {{ "title": "KFC", "amount": 20, "type": "expense", "category": "Food", "date": "today" }},
        {{ "title": "Gas", "amount": 50, "type": "expense", "category": "Transport", "date": "today" }}
    ]

    Input: "{user_text}"
    JSON:
    """
    response = llm_adapter.generate(prompt, max_tokens=300, temperature=0.1)
    print(response)
    result = clean_json_output(response)
    
    if isinstance(result, dict): return [result]
    return result or []
# ==========================================
# 💬 MODE 3: ANSWER GENERATOR (The Chatbot/RAG)
# ==========================================
def generate_answer(user_text: str, data_context: list = None):
    """
    Generates a natural language response.
    - If data_context is provided (RAG), answer based on that data.
    - If no data, just chat normally.
    """
    if data_context:
        # RAG MODE: Answer using DB data
        context_str = json.dumps(data_context)
        prompt = f"""
        You are FinBot. Answer the user's question based strictly on the provided data.
        
        USER QUESTION: "{user_text}"
        DATABASE RECORDS: {context_str}
        
        Summarize the totals or list specific items requested. Be friendly and concise.
        """
    else:
        # CHAT MODE: General conversation
        prompt = f"""
        You are FinBot, a helpful financial assistant. 
        The user is chatting with you. Be brief and professional.
        
        User: "{user_text}"
        Reply:
        """

    return llm_adapter.generate(prompt, max_tokens=256, temperature=0.7)

# --- TEST FLOW ---
if __name__ == "__main__":
    test_input = "I spent 500 on new headphones"
    
    # 1. Classify
    intent = classify_intent(test_input)
    print(f"🧠 Intent: {intent}")

    if intent.get("intent") == "create":
        # 2. Extract
        data = extract_transactions(test_input)
        print(f"📝 Extracted Data: {data}")
    
    elif intent.get("intent") == "query":
        # Simulate DB fetch
        fake_db_data = [{"title": "Headphones", "amount": 500}]
        # 3. Answer
        reply = generate_answer(test_input, fake_db_data)
        print(f"💬 Bot Reply: {reply}")