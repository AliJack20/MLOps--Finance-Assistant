# src/data_ingestion.py
"""
Data ingestion and preprocessing utilities.
Designed to mirror the preprocessing in ExtraTrees_Regressor.ipynb.
"""

import os
import pandas as pd
from sklearn.preprocessing import LabelEncoder
from typing import Tuple, List


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

# Columns to label encode (example: product_type, ecology in notebook)
LABEL_COLUMNS = ["product_type", "ecology"]


def load_csv(path: str) -> pd.DataFrame:
    """Load CSV into DataFrame."""
    df = pd.read_csv(path)
    return df


def drop_na(df: pd.DataFrame) -> pd.DataFrame:
    """Drop rows with NA values (same as notebook)."""
    target_col = 'price_doc'  # Replace with actual target column name
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
    df = load_csv(path)
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
