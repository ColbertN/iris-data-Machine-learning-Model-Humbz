"""Lightweight, dependency-free feature and prediction monitoring."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from iris_model.config import FEATURE_COLUMNS


def build_baseline(features: pd.DataFrame, bins: int = 10) -> dict:
    """Capture training feature distributions used as monitoring reference."""
    reference: dict[str, object] = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "reference_rows": int(len(features)),
        "features": {},
    }
    for column in FEATURE_COLUMNS:
        values = features[column].to_numpy(dtype=float)
        quantiles = np.quantile(values, np.linspace(0, 1, bins + 1))
        edges = np.unique(quantiles)
        if len(edges) < 2:
            edges = np.array([values.min() - 0.5, values.max() + 0.5])
        edges[0] = -np.inf
        edges[-1] = np.inf
        counts, _ = np.histogram(values, bins=edges)
        expected_rate = (counts / counts.sum()).tolist()
        reference["features"][column] = {
            "bin_edges": [float(edge) for edge in edges],
            "expected_rate": expected_rate,
            "mean": float(values.mean()),
            "std": float(values.std(ddof=0)),
            "minimum": float(values.min()),
            "maximum": float(values.max()),
        }
    return reference


def save_baseline(baseline: dict, path: str | Path) -> None:
    Path(path).write_text(json.dumps(baseline, indent=2), encoding="utf-8")


def load_baseline(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def psi_level(psi: float) -> str:
    """Conventional PSI bands; use as an alert signal, not proof of degradation."""
    if psi < 0.10:
        return "low"
    if psi < 0.25:
        return "moderate"
    return "high"


def feature_drift(features: pd.DataFrame, baseline: dict) -> pd.DataFrame:
    """Calculate population stability index and simple range checks per feature."""
    results = []
    epsilon = 1e-6
    for column in FEATURE_COLUMNS:
        current = features[column].to_numpy(dtype=float)
        spec = baseline["features"][column]
        edges = np.asarray(spec["bin_edges"], dtype=float)
        expected = np.asarray(spec["expected_rate"], dtype=float)
        counts, _ = np.histogram(current, bins=edges)
        actual = counts / max(counts.sum(), 1)
        psi = float(np.sum((actual - expected) * np.log((actual + epsilon) / (expected + epsilon))))
        outside_range = np.mean((current < spec["minimum"]) | (current > spec["maximum"]))
        results.append(
            {
                "feature": column,
                "reference_mean": spec["mean"],
                "current_mean": float(current.mean()),
                "mean_shift": float(current.mean() - spec["mean"]),
                "psi": psi,
                "drift_level": psi_level(psi),
                "outside_training_range_rate": float(outside_range),
            }
        )
    return pd.DataFrame(results).sort_values("psi", ascending=False).reset_index(drop=True)


def prediction_distribution(predictions, class_names) -> pd.DataFrame:
    """Create a complete class distribution, including zero-count classes."""
    observed = pd.Series(predictions).value_counts()
    frame = pd.DataFrame({"predicted_species": class_names})
    frame["count"] = frame["predicted_species"].map(observed).fillna(0).astype(int)
    frame["proportion"] = frame["count"] / max(len(predictions), 1)
    return frame


def monitoring_summary(drift: pd.DataFrame, row_count: int) -> dict:
    """Summarize a batch into a machine-readable monitoring status."""
    high = int((drift["drift_level"] == "high").sum())
    moderate = int((drift["drift_level"] == "moderate").sum())
    status = "alert" if high else "review" if moderate else "healthy"
    return {
        "scored_at_utc": datetime.now(timezone.utc).isoformat(),
        "batch_rows": int(row_count),
        "status": status,
        "high_drift_features": high,
        "moderate_drift_features": moderate,
        "maximum_psi": float(drift["psi"].max()) if not drift.empty else 0.0,
        "note": "PSI flags distribution movement. Investigate data quality and model performance before retraining.",
    }
