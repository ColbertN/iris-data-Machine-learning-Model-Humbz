"""Model-agnostic SHAP report generation."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def _transformed_features(model, features: pd.DataFrame) -> np.ndarray:
    """Apply pipeline preprocessing while leaving the final estimator untouched."""
    if hasattr(model, "steps") and len(model.steps) > 1:
        return model[:-1].transform(features)
    return np.asarray(features)


def _feature_importance_from_values(values) -> np.ndarray:
    """Reduce SHAP's version/model-specific output shapes to one importance per feature."""
    if isinstance(values, list):
        array = np.stack([np.asarray(item) for item in values], axis=-1)
    else:
        array = np.asarray(values.values if hasattr(values, "values") else values)
    if array.ndim == 2:
        return np.abs(array).mean(axis=0)
    if array.ndim == 3:
        # The normalized representation is (row, feature, class).
        return np.abs(array).mean(axis=(0, 2))
    raise ValueError(f"Unexpected SHAP value shape: {array.shape}")


def generate_shap_report(
    model,
    background: pd.DataFrame,
    explain: pd.DataFrame,
    output_csv: str | Path,
    output_plot: str | Path,
    output_markdown: str | Path,
) -> pd.DataFrame:
    """Explain the selected classifier and save global mean-absolute SHAP importance.

    Tree and linear estimators use their fast native explainers. Other selected
    models use SHAP's permutation explainer, which is practical for this small data set.
    """
    import shap  # Slow optional import is isolated from ordinary scoring.

    estimator = model.steps[-1][1] if hasattr(model, "steps") else model
    transformed_background = _transformed_features(model, background)
    transformed_explain = _transformed_features(model, explain)
    estimator_name = estimator.__class__.__name__

    if estimator_name in {"RandomForestClassifier", "ExtraTreesClassifier", "GradientBoostingClassifier"}:
        explainer = shap.TreeExplainer(estimator)
        values = explainer.shap_values(transformed_explain)
        explainer_kind = "TreeExplainer"
    elif estimator_name == "LogisticRegression" or (
        estimator_name == "SVC" and getattr(estimator, "kernel", None) == "linear"
    ):
        explainer = shap.LinearExplainer(estimator, transformed_background)
        values = explainer.shap_values(transformed_explain)
        explainer_kind = "LinearExplainer"
    else:
        background_sample = shap.sample(transformed_background, min(40, len(transformed_background)), random_state=42)
        explainer = shap.PermutationExplainer(estimator.predict_proba, background_sample)
        values = explainer(transformed_explain, max_evals=2 * transformed_explain.shape[1] + 1)
        explainer_kind = "PermutationExplainer"

    importance = _feature_importance_from_values(values)
    feature_names = list(background.columns)
    result = pd.DataFrame({"feature": feature_names, "mean_abs_shap_value": importance})
    result = result.sort_values("mean_abs_shap_value", ascending=False).reset_index(drop=True)
    result.to_csv(output_csv, index=False)

    figure, axis = plt.subplots(figsize=(8, 4.5))
    ordered = result.sort_values("mean_abs_shap_value")
    axis.barh(ordered["feature"], ordered["mean_abs_shap_value"], color="#59A14F")
    axis.set_title("Global SHAP feature importance")
    axis.set_xlabel("Mean absolute SHAP value")
    figure.tight_layout()
    figure.savefig(output_plot, dpi=180, bbox_inches="tight")
    plt.close(figure)

    top = result.iloc[0]
    Path(output_markdown).write_text(
        "# SHAP explanation\n\n"
        f"- Explainer: `{explainer_kind}`\n"
        f"- Explained rows: {len(explain)}\n"
        f"- Most influential feature globally: `{top['feature']}` "
        f"(mean |SHAP| = {top['mean_abs_shap_value']:.4f})\n\n"
        "Values measure each feature's average contribution magnitude to the selected model's class probabilities; they do not prove causation.\n",
        encoding="utf-8",
    )
    return result
