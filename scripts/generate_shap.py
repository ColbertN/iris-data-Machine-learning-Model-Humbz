"""Create SHAP outputs for the persisted winning Iris model in an isolated process."""

from __future__ import annotations

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import joblib
from sklearn.model_selection import train_test_split

from iris_model.config import FIGURES_DIR, MODELS_DIR, RANDOM_STATE, REPORTS_DIR, TEST_SIZE, ensure_output_directories
from iris_model.data import features_and_target, load_data
from iris_model.explainability import generate_shap_report


def main(exit_cleanly_on_windows: bool = False) -> None:
    ensure_output_directories()
    model_path = MODELS_DIR / "iris_classifier.joblib"
    if not model_path.exists():
        raise FileNotFoundError(f"Saved model not found at {model_path}. Run train_compare.py first.")
    data = load_data()
    features, target = features_and_target(data)
    x_train, x_test, _, _ = train_test_split(
        features, target, test_size=TEST_SIZE, stratify=target, random_state=RANDOM_STATE
    )
    generate_shap_report(
        joblib.load(model_path),
        x_train,
        x_test,
        REPORTS_DIR / "shap_feature_importance.csv",
        FIGURES_DIR / "shap_feature_importance.png",
        REPORTS_DIR / "shap_summary.md",
    )
    print("SHAP explanation complete.")
    # SHAP/Numba can hang while cleaning local explainer objects on Windows.
    # This script is an isolated report worker, so all required files have
    # already been closed and no in-memory state needs a normal interpreter exit.
    if exit_cleanly_on_windows and sys.platform == "win32":
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(0)


if __name__ == "__main__":
    main(exit_cleanly_on_windows=True)
