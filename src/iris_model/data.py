"""Data loading and validation helpers."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd

from iris_model.config import DATA_CANDIDATES, FEATURE_COLUMNS, ID_COLUMN, TARGET_COLUMN


def resolve_default_data_path() -> Path:
    """Return the first expected Iris CSV location that exists."""
    for path in DATA_CANDIDATES:
        if path.exists():
            return path
    expected = " or ".join(str(path) for path in DATA_CANDIDATES)
    raise FileNotFoundError(f"Iris data was not found. Expected {expected}.")


def load_data(path: str | Path | None = None, require_target: bool = True) -> pd.DataFrame:
    """Load a CSV and enforce the schema needed by the workflow."""
    csv_path = Path(path) if path is not None else resolve_default_data_path()
    if not csv_path.exists():
        raise FileNotFoundError(f"Input data does not exist: {csv_path}")

    frame = pd.read_csv(csv_path)
    required = set(FEATURE_COLUMNS)
    if require_target:
        required.add(TARGET_COLUMN)
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise ValueError(
            f"{csv_path} is missing required column(s): {missing}. "
            f"Expected measurements: {FEATURE_COLUMNS}."
        )

    result = frame.copy()
    for feature in FEATURE_COLUMNS:
        result[feature] = pd.to_numeric(result[feature], errors="coerce")
    if result[FEATURE_COLUMNS].isna().any().any():
        invalid = result[FEATURE_COLUMNS].isna().sum()
        invalid = invalid[invalid.gt(0)].to_dict()
        raise ValueError(f"Feature columns contain missing or non-numeric values: {invalid}")
    if require_target and result[TARGET_COLUMN].isna().any():
        raise ValueError(f"{TARGET_COLUMN} contains missing values.")
    return result


def features_and_target(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """Return model features and the species label, excluding the record identifier."""
    return frame.loc[:, FEATURE_COLUMNS].copy(), frame.loc[:, TARGET_COLUMN].copy()


def dataset_fingerprint(path: str | Path) -> str:
    """Create a SHA-256 fingerprint for traceability in model metadata."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as input_file:
        for chunk in iter(lambda: input_file.read(65_536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def descriptive_columns(frame: pd.DataFrame) -> list[str]:
    """Return identifier, features, and label that should appear in profiling output."""
    return [column for column in [ID_COLUMN, *FEATURE_COLUMNS, TARGET_COLUMN] if column in frame.columns]
