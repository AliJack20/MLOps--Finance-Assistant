
import pandas as pd
import mlflow
from sentence_transformers import SentenceTransformer, util
import json
import os
import sys

# Adjust Python path to import prompt functions from the parent directory
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from zero_shot import get_zero_shot_prompt
from few_shot import get_few_shot_prompt
from chain_of_thought import get_cot_prompt

# --- Setup ---
# Initialize the sentence transformer model
model = SentenceTransformer('all-MiniLM-L6-v2')

# Set the MLflow experiment
mlflow.set_experiment("Finance_Prompt_Experiments")

# --- Mock LLM Function ---
def call_llm(prompt: str) -> str:
    """
    Placeholder for a real LLM call. 
    
    Instructions:
    Replace the content of this function with your actual API call to a Large Language Model.
    For example, you could use libraries like 'openai', 'google-generativeai', or a local model via 'ollama'.
    
    Example with OpenAI:
    --------------------
    # from openai import OpenAI
    # client = OpenAI(api_key="YOUR_API_KEY")
    # response = client.chat.completions.create(
    #   model="gpt-3.5-turbo",
    #   messages=[{"role": "system", "content": prompt}]
    # )
    # return response.choices[0].message.content
    """
    print(f"--- PROMPT --- \n{prompt}\n----------------")
    return "This is a simulated response for testing the pipeline. It is not a real financial answer."

# --- Evaluation Logic ---
def evaluate_strategy(strategy_name: str, data: list, k: int = None):
    """
    Runs the evaluation for a given prompt strategy, logs results to MLflow, and saves artifacts.
    """
    run_name = f"{strategy_name}" + (f"_k={k}" if k is not None else "")
    
    with mlflow.start_run(run_name=run_name):
        print(f"--- Running Evaluation for: {run_name} ---")
        
        results = []
        total_similarity = 0
        
        for item in data:
            question = item['question']
            ground_truth = item['ground_truth']
            
            # 1. Generate Prompt
            if strategy_name == "Zero-Shot":
                prompt = get_zero_shot_prompt(question)
            elif strategy_name == "Few-Shot":
                prompt = get_few_shot_prompt(question, k=k)
            elif strategy_name == "Chain-of-Thought":
                prompt = get_cot_prompt(question)
            else:
                raise ValueError(f"Unknown strategy: {strategy_name}")

            # 2. Get Model Response
            model_response = call_llm(prompt)
            
            # 3. Calculate Cosine Similarity
            embedding_1 = model.encode(model_response, convert_to_tensor=True)
            embedding_2 = model.encode(ground_truth, convert_to_tensor=True)
            score = util.pytorch_cos_sim(embedding_1, embedding_2).item()
            total_similarity += score
            
            results.append({
                "question": question,
                "ground_truth": ground_truth,
                "model_response": model_response,
                "score": score
            })

        # 4. Log Metrics and Parameters to MLflow
        avg_cosine_sim = total_similarity / len(data)
        mlflow.log_metric("avg_cosine_sim", avg_cosine_sim)
        
        params = {"strategy": strategy_name}
        if k is not None:
            params["k"] = k
        mlflow.log_params(params)
        
        # 5. Save and Log Artifact
        results_df = pd.DataFrame(results)
        csv_filename = f"results_{run_name.replace(' ', '_').lower()}.csv"
        results_df.to_csv(csv_filename, index=False)
        mlflow.log_artifact(csv_filename)
        
        print(f"Average Cosine Similarity for {run_name}: {avg_cosine_sim:.4f}")
        print(f"Results saved to {csv_filename}")
        print("-" * 50)

def main():
    """
    Main function to run the entire evaluation pipeline.
    """
    # Load the evaluation dataset
    eval_data_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'eval.jsonl')
    with open(eval_data_path, 'r') as f:
        data = [json.loads(line) for line in f]

    # Define the evaluation configurations
    configurations = [
        {"strategy": "Zero-Shot", "k": None},
        {"strategy": "Few-Shot", "k": 1},
        {"strategy": "Few-Shot", "k": 3},
        {"strategy": "Chain-of-Thought", "k": None},
    ]

    # Loop through configurations and run evaluations
    for config in configurations:
        evaluate_strategy(strategy_name=config["strategy"], data=data, k=config["k"])

if __name__ == "__main__":
    main()
