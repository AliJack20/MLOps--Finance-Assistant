# experiments/scripts/run_prompts.py
import os
import json
import time
from pathlib import Path
from typing import Dict, Any, List
import mlflow
import numpy as np
import inspect
import types


from src.rag_app.llm import llm_adapter
from src.rag_app.rag import RAG,EMB_MODEL

# For token estimation / metrics (try to reuse RAG Embeddings)
def get_embeddings_instance():
    try:
        rag = RAG(docs_folder="src/rag_app/data", index_path="src/rag_app/embeddings_cache/faiss_index")
        return rag.embeddings
    except Exception:
        # create a local embeddings object (same class used in RAG)
        from src.rag_app.rag import Embeddings
        return Embeddings(model_name=EMB_MODEL)

EMB = get_embeddings_instance()

def cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    if a is None or b is None: return 0.0
    denom = (np.linalg.norm(a) * np.linalg.norm(b))
    return float(np.dot(a, b) / denom) if denom!=0 else 0.0

def load_eval(path: str) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]

def load_prompt_template(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")

def build_prompt(template: str, query: str, context: str = None) -> str:
    p = template.replace("{query}", query)
    if context:
        # naive insertion if templates expect {context} token
        p = p.replace("{context}", context)
    return p

def _call_generate_flexible(llm, prompt: str, system_prompt: str = "", max_tokens: int = 256, temperature: float = 0.7):
    """
    Call llm.generate using a signature-flexible strategy:
      - Try (prompt, system_prompt, max_tokens, temperature)
      - Then (prompt, system_prompt, max_tokens)
      - Then (prompt, system_prompt)
      - Then (prompt,)
    If none work, raise a helpful TypeError showing the adapter signature.
    """
    # If llm is a function (not instance method), call directly
    if isinstance(llm, types.FunctionType):
        try:
            return llm(prompt, system_prompt, max_tokens, temperature)
        except TypeError:
            pass

    # Try progressively smaller positional argument counts
    attempts = [
        (prompt, system_prompt, max_tokens, temperature),
        (prompt, system_prompt, max_tokens),
        (prompt, system_prompt),
        (prompt,),
    ]

    last_exc = None
    for args in attempts:
        try:
            return llm.generate(*args)
        except TypeError as e:
            last_exc = e
            continue

    # nothing worked — show adapter signature to help debugging
    try:
        sig = inspect.signature(llm.generate)
    except Exception:
        sig = None
    raise TypeError(
        "Unable to call llm.generate with common signatures. "
        f"Adapter signature: {sig}; last error: {last_exc}"
    )


def run_one_strategy(strategy_name: str, template_path: str, eval_data, out_dir, include_context=False, max_tokens=256, temp=0.2):
    template = load_prompt_template(template_path)
    run_id = f"{strategy_name}"
    os.makedirs(out_dir, exist_ok=True)
    results = []
    # If an MLflow run is already active, start nested run; else start top-level run.
    nested_flag = mlflow.active_run() is not None

    with mlflow.start_run(run_name=run_id, nested=nested_flag):
        mlflow.log_param("strategy", strategy_name)
        mlflow.log_param("template_path", template_path)
        mlflow.log_param("include_context", include_context)
        for ex in eval_data:
            qid = ex["id"]
            q = ex["query"]
            gold = ex.get("gold_answer","")
            # optionally get RAG context
            context = ""
            if include_context:
                local_rag = RAG(docs_folder="src/rag_app/data", index_path="src/rag_app/embeddings_cache/faiss_index")
                local_rag.build_index_if_missing()
                context = local_rag.get_context(q, k=4)
            prompt = build_prompt(template, q, context)
            t0 = time.perf_counter()
            out = llm_adapter.generate(prompt, max_tokens, temp)

            latency = time.perf_counter() - t0

            # embeddings similarity metric
            try:
                ans_vec = EMB.embed_query(out)
                gold_vec = EMB.embed_query(gold)
                sim = cosine_sim(ans_vec, gold_vec)
            except Exception:
                sim = 0.0

            rec = {"id": qid, "query": q, "gold": gold, "answer": out, "latency": latency, "sim": sim}
            results.append(rec)

            # log per-sample as artifact or metric
            # Use a stable step; use an incrementing counter instead of parsing ids if needed
            mlflow.log_metric("sim", sim)
            mlflow.log_metric("latency", latency)

        # aggregate metrics for run
        sims = [r["sim"] for r in results]
        latencies = [r["latency"] for r in results]
        if sims:
            mlflow.log_metric("sim_mean", float(np.mean(sims)))
            mlflow.log_metric("sim_median", float(np.median(sims)))
        if latencies:
            mlflow.log_metric("latency_mean", float(np.mean(latencies)))
        # save results artifact
        out_file = os.path.join(out_dir, f"{strategy_name}_results.jsonl")
        with open(out_file, "w", encoding="utf-8") as f:
            for r in results:
                f.write(json.dumps(r) + "\n")
        mlflow.log_artifact(out_file, artifact_path="prompt_results")

    return out_file


# experiments/scripts/run_prompts.py
# ... (existing imports and functions above)

def run_all_prompts(eval_path: str = "data/eval.jsonl",
                    out_base: str = "results/prompt_runs",
                    strategies: list = None,
                    include_context: bool = False,
                    max_tokens: int = 256,
                    temp: float = 0.2):
    """
    Programmatic entrypoint so other scripts (e.g., src/train.py) can call
    the prompt experiment runner.

    - eval_path: path to JSONL evaluation file
    - out_base: directory to write results
    - strategies: list of tuples (name, template_path) — if None uses the default set
    """
    if strategies is None:
        strategies = [
            ("baseline", "experiments/prompts/baseline.txt"),
            ("fewshot_k3", "experiments/prompts/few_shot_k3.txt"),
            ("fewshot_k5", "experiments/prompts/few_shot_k5.txt"),
            ("cot", "experiments/prompts/advanced_cot.txt"),
            ("meta", "experiments/prompts/advanced_meta.txt"),
        ]

    eval_data = load_eval(eval_path)
    os.makedirs(out_base, exist_ok=True)
    produced = []
    for name, tpl in strategies:
        print("Running prompt strategy:", name)
        out_file = run_one_strategy(
            strategy_name=name,
            template_path=tpl,
            eval_data=eval_data,
            out_dir=out_base,
            include_context=include_context,
            max_tokens=max_tokens,
            temp=temp
        )
        produced.append(out_file)
    return produced

def main():
    eval_path = "data/eval.jsonl"
    eval_data = load_eval(eval_path)
    out_base = "results/prompt_runs"
    strategies = [
        ("baseline", "experiments/prompts/baseline.txt", False),
        ("fewshot_k3", "experiments/prompts/few_shot_k3.txt", False),
        ("fewshot_k5", "experiments/prompts/few_shot_k5.txt", False),
        ("cot", "experiments/prompts/advanced_cot.txt", False),
        ("meta", "experiments/prompts/advanced_meta.txt", False),
    ]
    for name, tpl, include_context in strategies:
        print("Running:", name)
        run_one_strategy(name, tpl, eval_data, out_base, include_context=include_context)

if __name__ == "__main__":
    main()




