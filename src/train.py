# src/train.py
"""
Train script:
- Loads data via data_ingestion.full_pipeline_from_csv from S3 bucket
- Trains ExtraTreesRegressor (same hyperparams as your notebook)
- Logs metrics and model to MLflow (configured to use MLFLOW_TRACKING_URI env var)
- Uploads a copy of the fitted model as modeals/latest_model.pkl to S3 (S3_BUCKET env)
- Starts EC2 instance and Docker build and run through ssh
-Exposes FastAPI
-Shuts down instance after 10 minutes
"""

import os
import sys
import tempfile
import joblib
import mlflow
import mlflow.sklearn
import boto3
import logging
from sklearn.ensemble import ExtraTreesRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import root_mean_squared_error, r2_score
from dotenv import load_dotenv
import time
import numpy as np
import importlib
from pathlib import Path

from data_ingestion import full_pipeline_from_csv
from aws_utils import start_ec2_instance, stop_ec2_instance, run_docker_commands_on_ec2

# from monitoring.evidently_dashboard import generate_data_drift_report

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from experiments.scripts.run_prompts import run_all_prompts
from src.rag_app.rag import RAG
from src.rag_app.llm import generate_answer, classify_intent

# Hyperparameters (from notebook)
N_ESTIMATORS = int(os.getenv("N_ESTIMATORS", 100))
RANDOM_STATE = int(os.getenv("RANDOM_STATE", 42))
TEST_SIZE = float(os.getenv("TEST_SIZE", 0.2))

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

mode = os.getenv("MODE")
# print(mode)

if mode == "local":
    MLFLOW_TRACKING_URI = "file:./mlruns"
    S3_BUCKET = "local_bucket"
    print("local")
else:
    MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI")
    S3_BUCKET = os.getenv("S3_BUCKET")
    # problem already exists here.
    print("cloud")


# Env / AWS/MLflow config
# MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI")  # e.g. s3://bucket/mlflow/
# S3_BUCKET = os.getenv("S3_BUCKET")
S3_MODEL_KEY = os.getenv("S3_MODEL_KEY")
TRAIN_CSV = os.getenv("TRAIN_CSV", "data/train_spending.csv")
S3_TRAIN_KEY = os.getenv("S3_TRAIN_KEY")
S3_TEST_KEY = os.getenv("S3_TEST_KEY")
MLFLOW_EXPERIMENT = os.getenv("MLFLOW_EXPERIMENT", "mlops-demo")
aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
aws_secret_access = os.getenv("AWS_SECRET_ACCESS_KEY")
API_INSTANCE_ID = os.getenv("API_INSTANCE_ID")
region = os.getenv("AWS_REGION")


def upload_file_to_s3(local_path: str, bucket: str, key: str):
    """Upload a file to S3 at s3://{bucket}/{key} using boto3 and env creds."""
    s3 = boto3.client(
        "s3",
        aws_access_key_id=aws_access_key,
        aws_secret_access_key=aws_secret_access,
        region_name=region,
    )
    logger.info("Uploading %s to s3://%s/%s", local_path, bucket, key)
    s3.upload_file(local_path, bucket, key)
    logger.info("Upload finished")


def main():

    public_ip = start_ec2_instance(API_INSTANCE_ID, region)
    run_docker_commands_on_ec2(API_INSTANCE_ID, region, "MLOps pair.pem")
    print(f"Finance Aisstant API is live at: http://{public_ip}:8000/docs for 10 Minutes")
    time.sleep(600)  # Runs for 10 Minutes
    # Stop EC2 and docker
    stop_ec2_instance(API_INSTANCE_ID, region, "MLOps pair.pem")

    if not MLFLOW_TRACKING_URI:
        raise EnvironmentError(
            "Set MLFLOW_TRACKING_URI in environment (e.g. s3://bucket/mlflow/)"
        )
    if not S3_BUCKET:
        raise EnvironmentError("Set S3_BUCKET in environment")

    logger.info("MLflow tracking URI: %s", MLFLOW_TRACKING_URI)
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow.set_experiment(MLFLOW_EXPERIMENT)

    # Load data
    logger.info("Loading and preprocessing data from %s", TRAIN_CSV)
    X, y = full_pipeline_from_csv(TRAIN_CSV)

    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=TEST_SIZE, random_state=RANDOM_STATE
    )

    rag = RAG(docs_folder="src/rag_app/data", index_path="embeddings_cache/faiss_index")
    rag.build_index_if_missing()

    # Run query
    res = rag.query("What are government bonds?", k=4)

    rag_prompt = res["prompt"]
    #print("This is RAG output",rag_prompt)

    #time.sleep(100)

    # Get LLM answer
    # user_input = "What are goverment bonds"
    # intent_json = get_intent(user_input)
    # print("Detected Intent:", intent_json)
    # final_response = get_answer(user_input, rag_prompt)
    # print("Bot Answer:", final_response)
    # logger.info("Bot Answer: %s", final_response)

    #time.sleep(100)

    with mlflow.start_run():
        logger.info("Training ExtraTreesRegressor (n_estimators=%s)", N_ESTIMATORS)
        model = ExtraTreesRegressor(
            n_estimators=N_ESTIMATORS, n_jobs=-1, random_state=RANDOM_STATE, min_samples_split=4,bootstrap=False
        )
        print("X dtype:", X.dtype, "shape:", X.shape)
        print("y dtype:", y.dtype, "shape:", y.shape)
        assert np.issubdtype(X.dtype, np.floating), "X must be float dtype"
        assert np.issubdtype(y.dtype, np.floating), "y must be float dtype"

        model.fit(X_train, y_train)

        # Eval
        preds = model.predict(X_val)
        rmse = root_mean_squared_error(y_val, preds)
        r2 = r2_score(y_val, preds)

        logger.info("Validation RMSE: %.4f, R2: %.4f", rmse, r2)

        # Log metrics
        mlflow.log_metric("rmse", float(rmse))
        mlflow.log_metric("r2", float(r2))
        mlflow.log_param("n_estimators", N_ESTIMATORS)
        mlflow.log_param("random_state", RANDOM_STATE)

        # Log model in MLflow (this will store artifacts to the MLflow tracking uri -> S3)
        mlflow.sklearn.log_model(model, name="model")

        try:
            logger.info("Starting prompt engineering experiments (run_all_prompts)...")
            # choose evaluation file and output directory (override with env if desired)
            EVAL_PATH = os.getenv("PROMPT_EVAL_JSONL", "data/eval.json")
            PROMPT_OUT = os.getenv("PROMPT_RESULTS_DIR", "results/prompt_runs")

            # If you want context in prompts, set include_context=True
            produced_files = run_all_prompts(
                eval_path=EVAL_PATH,
                out_base=PROMPT_OUT,
                include_context=True,   # set True to inject RAG context into prompts that have {context}
                max_tokens=256,
                temp=0.2
            )

            # Log artifacts to MLflow (optional nested run)
            # Start a nested MLflow run so prompt experiments are recorded under the same top-level run
            with mlflow.start_run(nested=True, run_name="prompt_experiments"):
                mlflow.log_param("prompt_eval_path", EVAL_PATH)
                for f in produced_files:
                    mlflow.log_artifact(f, artifact_path="prompt_results")
            logger.info("Prompt experiments finished. Artifacts: %s", produced_files)

        except Exception as e:
            logger.exception("Prompt experiments failed: %s", e)
        
        #exit()

        # Also save a copy to a temp file and upload to S3 as latest_model.pkl for inference script
        with tempfile.NamedTemporaryFile(suffix=".pkl", delete=False) as tf:
            joblib.dump(model, tf.name)
            local_model_path = tf.name

        # Upload to S3 (explicit)
        upload_file_to_s3(local_model_path, S3_BUCKET, S3_MODEL_KEY)
        logger.info("Model uploaded to s3://%s/%s", S3_BUCKET, S3_MODEL_KEY)

        # Log S3 location as tag/artifact
        mlflow.set_tag("s3_model_path", f"s3://{S3_BUCKET}/{S3_MODEL_KEY}")

    logger.info("Training and Prompt Experimenting run finished. MLflow run info available.")

    #time.sleep(100)

    # DATA DRIFT evidently
    # train_df = load_csv_from_s3(S3_BUCKET, S3_TRAIN_KEY)
    # test_df  = load_csv_from_s3(S3_BUCKET, S3_TEST_KEY)
    # generate_data_drift_report(train_df, test_df, "monitoring\evidently_htmls\data_drift_report.html")

    # Start EC2 instance and Docker that serves the API
    public_ip = start_ec2_instance(API_INSTANCE_ID, region)
    run_docker_commands_on_ec2(API_INSTANCE_ID, region, "MLOps pair.pem")
    print(f"Finance Aisstant API is live at: http://{public_ip}:8000/docs for 10 Minutes")
    time.sleep(600)  # Runs for 10 Minutes
    # Stop EC2 and docker
    stop_ec2_instance(API_INSTANCE_ID, region, "MLOps pair.pem")


if __name__ == "__main__":
    main()
