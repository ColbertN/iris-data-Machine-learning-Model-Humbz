"""Consistent model scoring and report writers."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    log_loss,
    precision_score,
    recall_score,
)


def metric_summary(y_true, y_pred, y_probability=None, labels=None) -> dict[str, float]:
    """Compute a compact, multiclass-friendly metric set."""
    metrics = {
        "accuracy": accuracy_score(y_true, y_pred),
        "balanced_accuracy": balanced_accuracy_score(y_true, y_pred),
        "precision_macro": precision_score(y_true, y_pred, average="macro", zero_division=0),
        "recall_macro": recall_score(y_true, y_pred, average="macro", zero_division=0),
        "f1_macro": f1_score(y_true, y_pred, average="macro", zero_division=0),
    }
    if y_probability is not None:
        metrics["log_loss"] = log_loss(y_true, y_probability, labels=labels)
    return {name: float(value) for name, value in metrics.items()}


def classification_frame(y_true, y_pred, labels) -> pd.DataFrame:
    """Return sklearn's class-level report as a tidy table."""
    report = classification_report(y_true, y_pred, labels=labels, output_dict=True, zero_division=0)
    return pd.DataFrame(report).transpose().rename_axis("label").reset_index()


def confusion_frame(y_true, y_pred, labels) -> pd.DataFrame:
    """Return an indexed confusion matrix suitable for CSV output."""
    matrix = confusion_matrix(y_true, y_pred, labels=labels)
    return pd.DataFrame(matrix, index=pd.Index(labels, name="actual"), columns=pd.Index(labels, name="predicted"))


def save_confusion_matrix(y_true, y_pred, labels, title: str, output_path: str | Path) -> None:
    """Save a labelled confusion-matrix heatmap."""
    matrix = confusion_frame(y_true, y_pred, labels)
    figure, axis = plt.subplots(figsize=(7, 5))
    sns.heatmap(matrix, annot=True, fmt="d", cmap="Blues", cbar=False, ax=axis)
    axis.set_title(title)
    axis.set_xlabel("Predicted species")
    axis.set_ylabel("Actual species")
    figure.tight_layout()
    figure.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close(figure)


def save_probability_confidence(y_probability: np.ndarray, output_path: str | Path) -> pd.DataFrame:
    """Write and plot prediction-confidence distribution for monitoring."""
    confidence = np.max(y_probability, axis=1)
    frame = pd.DataFrame({"prediction_confidence": confidence})
    figure, axis = plt.subplots(figsize=(7, 4))
    axis.hist(confidence, bins=np.linspace(0.0, 1.0, 11), color="#4C78A8", edgecolor="white")
    axis.set_title("Prediction confidence distribution")
    axis.set_xlabel("Maximum predicted probability")
    axis.set_ylabel("Rows")
    figure.tight_layout()
    figure.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close(figure)
    return frame
