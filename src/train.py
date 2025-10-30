# src/train.py
"""
Train script:
- Loads data via data_ingestion.full_pipeline_from_csv
- Trains ExtraTreesRegressor (same hyperparams as your notebook)
- Logs metrics and model to MLflow (configured to use MLFLOW_TRACKING_URI env var)
- Uploads a copy of the fitted model as models/latest_model.pkl to S3 (S3_BUCKET env)
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

from data_ingestion import full_pipeline_from_csv

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from monitoring.evidently_dashboard import generate_data_drift_report


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Hyperparameters (from notebook)
N_ESTIMATORS = int(os.getenv("N_ESTIMATORS", 2))
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
TRAIN_CSV = os.getenv("TRAIN_CSV", "data/train.csv")
MLFLOW_EXPERIMENT = os.getenv("MLFLOW_EXPERIMENT", "mlops-demo")
aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
aws_secret_access = os.getenv("AWS_SECRET_ACCESS_KEY")
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

    with mlflow.start_run():
        logger.info("Training ExtraTreesRegressor (n_estimators=%s)", N_ESTIMATORS)
        model = ExtraTreesRegressor(
            n_estimators=N_ESTIMATORS, n_jobs=-1, random_state=RANDOM_STATE
        )
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

        # Also save a copy to a temp file and upload to S3 as latest_model.pkl for inference script
        with tempfile.NamedTemporaryFile(suffix=".pkl", delete=False) as tf:
            joblib.dump(model, tf.name)
            # local_model_path = tf.name

        # Upload to S3 (explicit)
        # upload_file_to_s3(local_model_path, S3_BUCKET, S3_MODEL_KEY)
        # logger.info("Model uploaded to s3://%s/%s", S3_BUCKET, S3_MODEL_KEY)

        # Log S3 location as tag/artifact
        mlflow.set_tag("s3_model_path", f"s3://{S3_BUCKET}/{S3_MODEL_KEY}")

    logger.info("Training run finished. MLflow run info available.")

    # DATA DRIFT evidently
    train_path = r"D:\Ikhlas University\Semester 7\MLOPS\Project_Financial_Advisor\MLOps--Finance-Assistant\train.csv"
    test_path = r"D:\Ikhlas University\Semester 7\MLOPS\Project_Financial_Advisor\MLOps--Finance-Assistant\test.csv"
    generate_data_drift_report(train_path, test_path, "data_drift_report.html")


if __name__ == "__main__":
    main()
