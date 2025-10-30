# src/inference.py
import os
import boto3
import joblib
import pandas as pd
import logging
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

S3_BUCKET = os.getenv("S3_BUCKET")
S3_MODEL_KEY = os.getenv("S3_MODEL_KEY")
AWS_REGION = os.getenv("AWS_REGION")
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")

def download_model_from_s3(bucket=S3_BUCKET, key=S3_MODEL_KEY, local_path="models/model.pkl"):
    """Download model from S3 and return local path."""
    s3 = boto3.client(
        "s3",
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY,
        region_name=AWS_REGION,
    )
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    logger.info(f"Downloading model from s3://{bucket}/{key}")
    s3.download_file(bucket, key, local_path)
    return local_path

def load_model():
    """Load model from S3"""
    model_path = download_model_from_s3()
    model = joblib.load(model_path)
    logger.info("✅ Model loaded successfully")
    return model

def predict(model, X: pd.DataFrame):
    """Run model prediction"""
    preds = model.predict(X)
    return preds
