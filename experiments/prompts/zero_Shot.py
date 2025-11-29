
def get_zero_shot_prompt(user_query: str) -> str:
    """
    Constructs a zero-shot prompt for a financial assistant.

    Args:
        user_query: The user's financial question.

    Returns:
        A string containing the system and user messages.
    """
    system_message = "You are a helpful financial assistant. Provide accurate and concise answers to financial questions."
    prompt = f"System: {system_message}\nUser: {user_query}\nAssistant:"
    return prompt

if __name__ == '__main__':
    # Example usage:
    query = "What is the difference between a stock and a bond?"
    prompt = get_zero_shot_prompt(query)
    print(prompt)