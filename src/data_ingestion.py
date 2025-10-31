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
    target_col = "price_doc"  # Replace with actual target column name
    # Keep first 4 columns plus target
    cols_to_keep = df.columns[:4].tolist() + [target_col]
    df = df[cols_to_keep]
    return df.dropna(axis=0)


def basic_clean(df: pd.DataFrame) -> pd.DataFrame:
    """Apply basic cleaning used in notebook."""
    # Drop 'sub_area' if present (not useful per notebook)
    if "sub_area" in df.columns:
        df = df.drop(columns=["sub_area"])
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
    df: pd.DataFrame, target_col: str = "price_doc"
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
    path: str, target_col: str = "price_doc"
) -> Tuple[pd.DataFrame, pd.Series]:
    """Complete ingestion -> cleaned (X, y) from CSV path."""
    df = load_csv("s3://mlops-financeai-s3-bucket /datasets/train.csv")
    df = drop_na(df)
    df = basic_clean(df)
    df = encode_labels(df)
    df = map_booleans(df)
    X, y = prepare_features_target(df, target_col=target_col)
    return X, y


if __name__ == "__main__":
    # Quick local test (not executed in production)
    import os

    p = os.getenv("TRAIN_CSV", "data/train.csv")
    print("Loading:", p)
    X, y = full_pipeline_from_csv(p)
    print("X shape:", X.shape, "y shape:", y.shape)
