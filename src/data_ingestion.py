# src/data_ingestion.py
"""
Data ingestion and preprocessing utilities.
Designed to mirror the preprocessing in ExtraTrees_Regressor.ipynb.
"""

import os
import pandas as pd
from sklearn.preprocessing import LabelEncoder
from typing import Tuple, List
import io
import boto3
import logging
from dotenv import load_dotenv
import numpy as np

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))


# Columns known from the notebook that are boolean yes/no -> map to 0/1
BOOLEAN_COLUMNS = [
    "culture_objects_top_25",
    "thermal_power_plant_raion",
    "incineration_raion",
    "oil_chemistry_raion",
    "radiation_raion",
    "railroad_terminal_raion",
    "big_market_raion",
    "nuclear_reactor_raion",
    "detention_facility_raion",
    "big_road1_1line",
    "railroad_1line",
    "water_1line",
]

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Columns to label encode (example: product_type, ecology in notebook)
LABEL_COLUMNS = ["product_type", "ecology"]

S3_BUCKET = os.getenv("S3_BUCKET")
S3_TRAIN_KEY = os.getenv("S3_TRAIN_KEY")


def load_csv_from_s3(bucket: str, key: str) -> pd.DataFrame:
    """Load CSV from S3 into a pandas DataFrame."""
    s3 = boto3.client("s3")
    response = s3.get_object(Bucket=bucket, Key=key)
    return pd.read_csv(io.BytesIO(response["Body"].read()))


def load_csv(path: str) -> pd.DataFrame:
    """
    Load CSV from either a local path or an S3 path (s3://bucket/key).
    """
    if path.startswith("s3://"):
        try:
            s3 = boto3.client("s3")
            bucket, key = path.replace("s3://", "").split("/", 1)
            logger.info(f"Loading CSV from S3: bucket={S3_BUCKET}, key={S3_TRAIN_KEY}")
            response = s3.get_object(Bucket=S3_BUCKET, Key=S3_TRAIN_KEY)
            df = pd.read_csv(response["Body"])
            logger.info(f"Loaded dataset with shape {df.shape}")
            return df
        except Exception as e:
            logger.error(f"Failed to load CSV from S3: {e}")
            raise
    else:
        logger.info(f"Loading CSV from local path: {path}")
        df = pd.read_csv(path)
        return df


def drop_na(df: pd.DataFrame) -> pd.DataFrame:
    """Drop rows with NA values (same as notebook)."""
    target_col = "predicted_spending_next_week"  # Replace with actual target column name
    # Keep first 4 columns plus target
    #cols_to_keep = df.columns[:4].tolist() + [target_col]
    #df = df[cols_to_keep]
    return df.dropna(axis=0)


def basic_clean(df: pd.DataFrame) -> pd.DataFrame:
    # Ensure week is datetime (coerce invalid -> NaT)
    df["week"] = pd.to_datetime(df["week"], errors="coerce")

    # Drop rows with missing week or missing target/important features
    # (adjust the columns as per your dataset)
    df = df.dropna(subset=["week", "actual_spending", "predicted_spending_next_week"])

    # Sort by week to preserve chronological order
    df = df.sort_values("week").reset_index(drop=True)

    # Create a simple sequential week index (0,1,2,...). This is numeric and stable.
    df["week_num"] = np.arange(len(df), dtype=np.int64)

    # If you prefer epoch seconds instead of simple index:
    # df["week_ts"] = df["week"].astype("int64") // 10**9

    # Ensure numeric types for numeric columns (convert nullable pandas dtypes to numpy floats)
    numeric_cols = ["week_num", "actual_spending", "predicted_spending_next_week"]
    for c in numeric_cols:
        # convert to float64 (safe for sklearn)
        df[c] = pd.to_numeric(df[c], errors="coerce").astype(np.float64)

    return df


def encode_labels(
    df: pd.DataFrame, label_cols: List[str] = LABEL_COLUMNS
) -> pd.DataFrame:
    """Label-encode known categorical columns if present."""
    for col in label_cols:
        if col in df.columns:
            le = LabelEncoder()
            df[col] = le.fit_transform(df[col].astype(str))
    return df


def map_booleans(
    df: pd.DataFrame, bool_cols: List[str] = BOOLEAN_COLUMNS
) -> pd.DataFrame:
    """Map yes/no columns to 1/0 where present."""
    for col in bool_cols:
        if col in df.columns:
            df[col] = df[col].map({"yes": 1, "no": 0}).fillna(0).astype(int)
    return df


def prepare_features_target(
    df: pd.DataFrame, target_col: str = "predicted_spending_next_week"
) -> Tuple[pd.DataFrame, pd.Series]:
    """
    Split into features X and target y.
    Uses the notebook's convention: target column 'price_doc'.
    If target not present, raises KeyError.
    """
    if target_col not in df.columns:
        raise KeyError(f"Target column '{target_col}' not found in dataframe")
    # The notebook used iloc slicing but here we programmatically drop target
    X = df.drop(columns=[target_col])
    y = df[target_col]
    return X, y


def full_pipeline_from_csv(
    path: str, target_col: str = "predicted_spending_next_week"
) -> Tuple[pd.DataFrame, pd.Series]:
    """Complete ingestion -> cleaned (X, y) from CSV path."""
    df = load_csv("s3://mlops-financeai-s3-bucket /datasets/new_reg_train.csv")
    df = drop_na(df)
    df = basic_clean(df)

    # Choose features and target used in training
    feature_cols = ["week_num", "actual_spending"]  # adjust if you use week_ts or other engineered features
    target_col = "predicted_spending_next_week"

    # Ensure columns exist
    assert set(feature_cols + [target_col]).issubset(df.columns), "Missing columns in df"

    # Fill or drop NaNs (here we drop any rows with NaN in selected cols)
    df = df.dropna(subset=feature_cols + [target_col])

    X = df[feature_cols].astype(np.float64).to_numpy()   # shape (n_samples, n_features), dtype float64
    y = df[target_col].astype(np.float64).to_numpy()     # shape (n_samples,), dtype float64

    #df = encode_labels(df)
    #df = map_booleans(df)
    #X, y = prepare_features_target(df, target_col=target_col)
    return X, y


if __name__ == "__main__":
    # Quick local test (not executed in production)
    import os

    p = os.getenv("TRAIN_CSV", "data/train_spending.csv")
    print("Loading:", p)
    X, y = full_pipeline_from_csv(p)
    print("X shape:", X.shape, "y shape:", y.shape)
