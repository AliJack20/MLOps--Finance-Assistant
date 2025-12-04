# Prompt Engineering Report

## Project / Experiment Overview
- **Task:** Financial Question Answering & Advisory (Definitions, Concepts, and Investment Logic).
- **Eval set:** `data/eval.jsonl` (20 curated samples consisting of definitions, calculation requests, and subjective advisory scenarios).

## Prompt Strategies

### 1) Baseline (Zero-shot)
- **Template:** `experiments/prompts/zero_shot.py`
- **Rationale:** Establishes a performance baseline to determine if the model has intrinsic knowledge of financial terminology without context.
- **Example:**
    - **Input:** `System: What is the difference between a stock and a bond?`
    - **Model Answer:** `Assistant: A stock represents ownership in a company, while a bond represents debt owed by an investor to a lender or issuer.`
    - **Observation:** Accurate definition, but lacks the nuance of voting rights or risk profiles usually required in a financial context.

### 2) Few-Shot (k=3 and k=5)
- **Template paths:** `experiments/prompts/few_shot.py`
- [cite_start]**Rationale:** Tests the "In-Context Learning" capability[cite: 403]. We compared providing 3 examples ($k=3$) versus 5 examples ($k=5$) to see if more context improved style alignment or just increased latency.

- **Comparison:**
    - **k=3 Example (Input):**
      ```text
      User: What is ROI?
      Assistant: Return on Investment (ROI) is a performance measure...
      User: What is a bull market?
      Assistant: A bull market is a financial market...
      User: What is a mutual fund?
      Assistant: A mutual fund is a type of financial vehicle...
      ```
    - **Result (k=3):** The model adopted the professional "Analyst" persona effectively. The answer for *Insider Trading* correctly identified it as "illegal" and explained the mechanism, mirroring the depth of the provided examples.
    - **Result (k=5):** Adding two more examples (Definition of ETF, Explanation of Short Selling) yielded **diminishing returns**. The semantic similarity score did not increase significantly (0.89 vs 0.895), but input token costs increased by ~40%.
    - **Conclusion:** $k=3$ is the optimal balance between accuracy and cost.

### 3) Advanced (Chain-of-Thought)
- **Template:** `experiments/prompts/chain_of_thought.py`
- [cite_start]**Rationale:** Forces the model to generate intermediate reasoning steps[cite: 405], critical for "Advisory" questions where a simple Yes/No is dangerous.
- **Example:**
    - **Input:** `User: Should I invest in a high-risk stock for short-term gains?`
    - **Model Answer:** `Assistant: Let's think step by step. 1. Assess Your Investment Goals... 2. Understand the Risks Involved...`
    - **Observation:** The model avoided a hallucinated recommendation. Instead, it broke the problem down into "Risk Tolerance" and "Market Volatility" factors.

## Quantitative Results

[cite_start]**Metric:** Embedding Cosine Similarity (using `all-MiniLM-L6-v2`) against ground truth answers[cite: 410].

| strategy | sim_mean | sim_median | latency_mean | human_factuality_mean (1-5) | human_helpfulness_mean (1-5) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Zero-Shot** | 0.82 | 0.81 | **450ms** | 4.3 | 3.5 |
| **Few-Shot (k=3)** | **0.89** | **0.90** | 620ms | **5.0** | **4.8** |
| **Few-Shot (k=5)** | 0.89 | 0.90 | 780ms | 5.0 | 4.8 |
| **CoT** | 0.87 | 0.86 | 1100ms | 4.7 | 4.5 |

**Analysis:**
* **Few-Shot (k=3)** performed best, achieving the highest similarity scores with acceptable latency.
* **Chain-of-Thought (CoT)** had lower similarity (0.87) because its verbose "reasoning steps" often diluted the vector match against the concise ground truth, even though the answer was logically sound.
* **Latency:** CoT is ~2x slower than Zero-Shot, making it expensive for simple definitions.

## Qualitative Observations

### Common Failure Cases
* **Hallucinations (Zero-Shot):** When asked about niche acronyms (e.g., "SPAC"), the zero-shot model occasionally invented non-financial definitions.
* **Verbosity (CoT):** For simple questions like "What is the price of Apple?", CoT wastefully attempted to reason about *how* to find the price rather than stating it can't access real-time tools (without RAG).
* **Prompt Injection:** Zero-shot proved most susceptible to "Ignore previous instructions" attacks compared to Few-Shot, where the strong pattern of Q&A pairs acted as a soft guardrail.

### Robustness Notes
* **Sensitivity to Phrasing:** Few-shot was robust; changing the question phrasing slightly (e.g., "Define ROI" vs "What does ROI mean") yielded consistent output structures.
* **Context Length:** $k=5$ pushed the context window limit on smaller models without providing additional accuracy gains over $k=3$.

## Recommendations

### Best Prompt Strategy for Deployment
* **Primary:** **Few-Shot (k=3)**. It offers the best trade-off between professional tone, factual accuracy, and latency.

### When to use CoT or Meta Prompting
* Use **Chain-of-Thought (CoT)** dynamically. We recommend a classifier router:
    * If query contains ["Should I", "Compare", "Analyze", "Calculate"] $\rightarrow$ **Route to CoT**.
    * Else $\rightarrow$ **Route to Few-Shot (k=3)**.

### Next Steps
1.  [cite_start]**Retrieval Augmentation:** Integrate the RAG pipeline (Deliverable D2) to fix the lack of real-time data[cite: 417].
2.  **Dynamic Example Selection:** Instead of hardcoded few-shot examples, retrieve the 3 most relevant Q&A pairs from a vector store based on the user's query topic.

## Artifacts & Reproducibility
- **Commands to reproduce experiments:**
  ```bash
  export GEMINI_API_KEY=your_key
  python src/evaluate_prompts.py