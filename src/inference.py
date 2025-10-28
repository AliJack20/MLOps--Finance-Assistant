# src/inference.py
"""
Inference utilities and a small example/app entrypoint.
- Downloads models/latest_model.pkl from S3 and loads it with joblib.
- Provides `predict` function that accepts a 2D array-like or DataFrame.
"""

import os
import tempfile
import joblib
import boto3
import logging
import pandas as pd
from typing import Any, List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

S3_BUCKET = os.getenv("S3_BUCKET")
S3_MODEL_KEY = os.getenv("S3_MODEL_KEY", "models/model.pkl")


def download_model_from_s3(bucket: str = S3_BUCKET, key: str = S3_MODEL_KEY) -> str:
    """Download S3 object to a temporary local file and return its path."""
    if not bucket:
        raise EnvironmentError("S3_BUCKET environment variable is not set")
    s3 = boto3.client(
        "s3",
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        region_name=os.getenv("AWS_REGION"),
    )
    tmp = tempfile.NamedTemporaryFile(suffix=".pkl", delete=False)
    logger.info("Downloading s3://%s/%s to %s", bucket, key, tmp.name)
    s3.download_file(bucket, key, tmp.name)
    logger.info("Download complete")
    return tmp.name


def load_model(local_model_path: str = None):
    """Load joblib model from path (or download from S3 if not provided)."""
    if local_model_path is None:
        local_model_path = download_model_from_s3()
    model = joblib.load(local_model_path)
    return model


def predict(model: Any, X: pd.DataFrame) -> List:
    """Return model predictions as list. Accepts pandas DataFrame or 2D array-like."""
    if hasattr(X, "values"):
        input_data = X.values
    else:
        input_data = X
    preds = model.predict(input_data)
    return preds.tolist()


if __name__ == "__main__":
    # example usage:
    # Ensure env variables are set: S3_BUCKET, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION
    model = load_model()
    # Create a dummy sample -- user should replace with real preprocessed sample
    import numpy as np
    sample = np.zeros((1, model.n_features_in_))
    print("Running prediction on dummy sample...")
    print(predict(model, sample))
