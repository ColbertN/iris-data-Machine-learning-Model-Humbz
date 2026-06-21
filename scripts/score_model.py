"""Score an Iris batch and produce labelled metrics plus drift monitoring."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import joblib
import pandas as pd

from iris_model.config import FEATURE_COLUMNS, FIGURES_DIR, MODELS_DIR, MONITORING_DIR, REPORTS_DIR, TARGET_COLUMN, ensure_output_directories
from iris_model.data import load_data
from iris_model.evaluation import classification_frame, confusion_frame, metric_summary, save_confusion_matrix, save_probability_confidence
from iris_model.monitoring import feature_drift, load_baseline, monitoring_summary, prediction_distribution


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Score an Iris batch using the saved classifier.")
    parser.add_argument("--input", required=True, help="CSV with the four Iris measurement columns; Species is optional.")
    return parser.parse_args()


def main() -> None:
    arguments = parse_arguments()
    ensure_output_directories()
    model_path = MODELS_DIR / "iris_classifier.joblib"
    metadata_path = MODELS_DIR / "model_metadata.json"
    baseline_path = MODELS_DIR / "monitoring_baseline.json"
    for required in (model_path, metadata_path, baseline_path):
        if not required.exists():
            raise FileNotFoundError(f"Required training artifact not found: {required}. Run scripts/train_compare.py first.")

    batch = load_data(arguments.input, require_target=False)
    model = joblib.load(model_path)
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    classes = metadata["class_names"]
    features = batch[FEATURE_COLUMNS]
    prediction = model.predict(features)
    probability = model.predict_proba(features)

    scored = batch.copy()
    scored["predicted_species"] = prediction
    for index, class_name in enumerate(model.classes_):
        scored[f"probability_{class_name}"] = probability[:, index]
    scored["prediction_confidence"] = probability.max(axis=1)
    scored.to_csv(REPORTS_DIR / "scored_predictions.csv", index=False)

    confidence = save_probability_confidence(probability, FIGURES_DIR / "scoring_prediction_confidence.png")
    confidence.to_csv(MONITORING_DIR / "scoring_prediction_confidence.csv", index=False)
    baseline = load_baseline(baseline_path)
    drift = feature_drift(features, baseline)
    drift.to_csv(MONITORING_DIR / "feature_drift.csv", index=False)
    distribution = prediction_distribution(prediction, classes)
    distribution.to_csv(MONITORING_DIR / "prediction_distribution.csv", index=False)
    summary = monitoring_summary(drift, len(batch))

    labelled_metrics = None
    if TARGET_COLUMN in batch.columns:
        labelled_metrics = metric_summary(batch[TARGET_COLUMN], prediction, probability, classes)
        classification_frame(batch[TARGET_COLUMN], prediction, classes).to_csv(REPORTS_DIR / "scoring_classification_report.csv", index=False)
        confusion_frame(batch[TARGET_COLUMN], prediction, classes).to_csv(REPORTS_DIR / "scoring_confusion_matrix.csv")
        save_confusion_matrix(
            batch[TARGET_COLUMN], prediction, classes, "Scoring batch confusion matrix", FIGURES_DIR / "scoring_confusion_matrix.png"
        )
        summary["labelled_metrics"] = labelled_metrics
    else:
        summary["labelled_metrics"] = None
        summary["label_note"] = "Species was not supplied, so performance metrics cannot be calculated for this batch."

    (MONITORING_DIR / "monitoring_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (REPORTS_DIR / "scoring_summary.json").write_text(
        json.dumps(
            {"input": str(Path(arguments.input)), "rows_scored": len(batch), "monitoring_status": summary["status"], "metrics": labelled_metrics},
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Scored {len(batch)} rows. Monitoring status: {summary['status']}. Outputs written to {REPORTS_DIR}.")


if __name__ == "__main__":
    main()
