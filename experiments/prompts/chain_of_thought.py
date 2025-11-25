
def get_cot_prompt(user_query: str) -> str:
    """
    Constructs a Chain of Thought (CoT) prompt for a financial assistant.

    Args:
        user_query: The user's financial question.

    Returns:
        A string containing the CoT system and user messages.
    """
    system_message = (
        "You are a helpful financial assistant. Your task is to provide a detailed, step-by-step explanation "
        "before giving the final answer. Break down your reasoning process to ensure clarity and accuracy."
    )
    
    prompt = (
        f"System: {system_message}\n"
        f"User: {user_query}\n"
        "Assistant: Let's think step by step."
    )
    
    return prompt

if __name__ == '__main__':
    # Example usage:
    query = "Should I invest in a high-risk stock for short-term gains?"
    prompt = get_cot_prompt(query)
    print(prompt)
