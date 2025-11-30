from gradio_client import Client
import json
import os
from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))
# Connect to your Space
token=os.getenv("HF_TOKEN")
client = Client("MuhammadHamza33/mistral-7b-test",token="")

def get_intent(user_text):
    # 1. Define the System Prompt for "Detective Mode"
    detective_prompt = """
    You are a precise data classifier.
    Extract the 'search_term' from the user's request as JSON.
    Example: "How much on food?" -> {"search_term": "Food"}
    Output ONLY JSON.
    """
    
    # 2. Call API with (User Text, System Prompt, Max Tokens, Temp)
    # Note: We use 0.1 temp for logic/extraction so it's precise
    result = client.predict(
        user_text,          # User Message
        detective_prompt,   # System Message
        100,                # Max Tokens
        0.1,                # Temperature
        api_name="/generate"
    )
    return result

def get_answer(user_text, data_context):
    # 1. Define the System Prompt for "Advisor Mode"
    advisor_prompt = f"""
    You are FinBot, a friendly financial assistant.
    Use the provided data to answer the user.
    
    DATA CONTEXT:
    {data_context}
    """
    
    # 2. Call API with higher temperature (0.7) for better chat
    result = client.predict(
        user_text,
        advisor_prompt,
        200,
        0.7,
        api_name="/generate"
    )
    return result

# --- TEST FLOW ---
user_input = "How much did I spend on burgers?"

# Step A: Get Intent
intent_json = get_intent(user_input)
print(f"Detected Intent: {intent_json}") 
# (You would parse this JSON and run your Python Pandas search here...)

# Step B: Get Final Answer (Pretending we found $15)
final_response = get_answer(user_input, "User spent $15.00 on Burger King.")
print(f"Bot Answer: {final_response}")