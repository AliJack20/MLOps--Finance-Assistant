import random

# Hardcoded financial Q&A examples
FINANCIAL_EXAMPLES = [
    {
        "question": "What is ROI?",
        "answer": "Return on Investment (ROI) is a performance measure used to evaluate the efficiency of an investment. It is calculated as (Current Value of Investment - Cost of Investment) / Cost of Investment."
    },
    {
        "question": "What is a bull market?",
        "answer": "A bull market is a financial market of a group of securities in which prices are rising or are expected to rise. The term is most often used to refer to the stock market but can be applied to anything that is traded, such as bonds, real estate, currencies, and commodities."
    },
    {
        "question": "What is the P/E ratio?",
        "answer": "The Price-to-Earnings (P/E) ratio is a valuation metric that compares a company's current share price to its per-share earnings. It is calculated as Market Value per Share / Earnings Per Share (EPS)."
    },
    {
        "question": "What is diversification?",
        "answer": "Diversification is a risk management strategy that mixes a wide variety of investments within a portfolio. The rationale behind this technique is that a portfolio constructed of different kinds of assets will, on average, yield higher long-term returns and lower the risk of any individual holding or security."
    },
    {
        "question": "What is a mutual fund?",
        "answer": "A mutual fund is a type of financial vehicle made up of a pool of money collected from many investors to invest in securities like stocks, bonds, money market instruments, and other assets. Mutual funds are operated by professional money managers, who allocate the fund's assets and attempt to produce capital gains or income for the fund's investors."
    }
]

def get_few_shot_prompt(user_query: str, k: int = 3) -> str:
    """
    Constructs a few-shot prompt for a financial assistant with k examples.

    Args:
        user_query: The user's financial question.
        k: The number of examples to include in the prompt.

    Returns:
        A string containing the system message, k examples, and the user message.
    """
    system_message = "You are a helpful financial assistant. Provide accurate and concise answers to financial questions. Here are some examples:"

    # Handle k > len(examples) by using all available examples
    if k > len(FINANCIAL_EXAMPLES):
        k = len(FINANCIAL_EXAMPLES)

    # Select k examples if k > 0
    if k > 0:
        examples = random.sample(FINANCIAL_EXAMPLES, k)
        example_texts = []
        for ex in examples:
            example_texts.append(f"User: {ex['question']}\nAssistant: {ex['answer']}")
        system_message += "\n\n" + "\n\n".join(example_texts)

    prompt = f"System: {system_message}\n\nUser: {user_query}\nAssistant:"
    return prompt

if __name__ == '__main__':
    # Example usage:
    query = "What is insider trading?"
    
    print("--- Zero-Shot Example (k=0) ---")
    prompt_k0 = get_few_shot_prompt(query, k=0)
    print(prompt_k0)
    
    print("\n--- Few-Shot Example (k=3) ---")
    prompt_k3 = get_few_shot_prompt(query, k=3)
    print(prompt_k3)

    print("\n--- Few-Shot Example (k > max) ---")
    prompt_k_max = get_few_shot_prompt(query, k=10)
    print(prompt_k_max)