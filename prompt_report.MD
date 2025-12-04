# Prompt Engineering Report

## Project / Experiment Overview
- Task: <short description>
- Eval set: data/eval.jsonl (N samples)

## Prompt Strategies
### 1) Baseline (Zero-shot)
- Template: experiments/prompts/baseline.txt
- Rationale: short explanation
- Example (input → model answer): ...

### 2) Few-Shot (k=3 and k=5)
- Template paths: ...
- Show both k=3 and k=5 examples and how they change style/accuracy.

### 3) Advanced (CoT / Meta)
- Template: experiments/prompts/advanced_cot.txt
- Describe step-by-step or persona + structured output.

## Quantitative Results
- Table: strategy | sim_mean | sim_median | latency_mean | human_factuality_mean | human_helpfulness_mean
- Show a small table and analysis (which performed best).

## Qualitative Observations
- Common failure cases (hallucinations, verbosity, prompt injection sensitivity)
- Robustness notes: sensitivity to phrasing, to few-shot examples, to context length.

## Recommendations
- Best prompt strategy for deployment
- When to use CoT or meta prompting
- Next steps (iterative prompt tuning, dynamic example selection, retrieval augmentation)

## Artifacts & Reproducibility
- Commands to reproduce experiments: `python src/train.py`
- MLflow run IDs: ...
- Location of results: results/prompt_runs/
