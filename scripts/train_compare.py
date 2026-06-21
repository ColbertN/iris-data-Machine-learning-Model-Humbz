"""Tune, compare, explain, and save Iris classifiers."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GridSearchCV, StratifiedKFold, train_test_split
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

from iris_model.config import (
    CV_FOLDS,
    FEATURE_COLUMNS,
    FIGURES_DIR,
    MODELS_DIR,
    MONITORING_DIR,
    N_JOBS,
    RANDOM_STATE,
    REPORTS_DIR,
    TEST_SIZE,
    ensure_output_directories,
)
from iris_model.data import dataset_fingerprint, features_and_target, load_data, resolve_default_data_path
from iris_model.evaluation import classification_frame, confusion_frame, metric_summary, save_confusion_matrix, save_probability_confidence
from iris_model.monitoring import build_baseline, feature_drift, monitoring_summary, prediction_distribution, save_baseline


def candidate_searches() -> dict[str, tuple[Pipeline, object]]:
    """Define fair pipelines and compact, meaningful search grids."""
    return {
        "logistic_regression": (
            Pipeline([("scaler", StandardScaler()), ("model", LogisticRegression(max_iter=3_000, random_state=RANDOM_STATE))]),
            {"model__C": [0.01, 0.1, 1.0, 10.0, 100.0]},
        ),
        "knn": (
            Pipeline([("scaler", StandardScaler()), ("model", KNeighborsClassifier())]),
            {"model__n_neighbors": [3, 5, 7, 9, 11], "model__weights": ["uniform", "distance"], "model__p": [1, 2]},
        ),
        "random_forest": (
            Pipeline([("model", RandomForestClassifier(random_state=RANDOM_STATE, n_jobs=N_JOBS))]),
            {
                "model__n_estimators": [150, 300],
                "model__max_depth": [None, 4],
                "model__min_samples_leaf": [1, 2],
                "model__max_features": ["sqrt"],
            },
        ),
        "svm": (
            Pipeline([("scaler", StandardScaler()), ("model", SVC(probability=True, random_state=RANDOM_STATE))]),
            [
                {"model__kernel": ["linear"], "model__C": [0.1, 1.0, 10.0, 100.0]},
                {"model__kernel": ["rbf"], "model__C": [0.1, 1.0, 10.0, 100.0], "model__gamma": ["scale", "auto"]},
            ],
        ),
    }


def compact_cv_results(search: GridSearchCV) -> pd.DataFrame:
    """Keep all parameter trials and their key validation metrics for auditability."""
    results = pd.DataFrame(search.cv_results_)
    parameter_columns = [column for column in results.columns if column.startswith("param_")]
    columns = [
        "rank_test_f1_macro",
        *parameter_columns,
        "mean_test_f1_macro",
        "std_test_f1_macro",
        "mean_test_accuracy",
        "mean_test_balanced_accuracy",
        "mean_test_neg_log_loss",
        "mean_fit_time",
    ]
    return results.loc[:, columns].sort_values("rank_test_f1_macro").reset_index(drop=True)


def save_permutation_importance(model, features, target) -> pd.DataFrame:
    """Use hold-out permutation importance so every winning model is explainable."""
    result = permutation_importance(
        model,
        features,
        target,
        scoring="f1_macro",
        n_repeats=50,
        random_state=RANDOM_STATE,
        n_jobs=N_JOBS,
    )
    importance = pd.DataFrame(
        {
            "feature": FEATURE_COLUMNS,
            "permutation_importance_mean": result.importances_mean,
            "permutation_importance_std": result.importances_std,
        }
    ).sort_values("permutation_importance_mean", ascending=False)
    importance.to_csv(REPORTS_DIR / "feature_importance.csv", index=False)
    return importance


def main(exit_cleanly_on_windows: bool = False) -> None:
    ensure_output_directories()
    dataset_path = resolve_default_data_path()
    data = load_data(dataset_path)
    features, target = features_and_target(data)
    class_names = sorted(target.unique())
    x_train, x_test, y_train, y_test = train_test_split(
        features, target, test_size=TEST_SIZE, stratify=target, random_state=RANDOM_STATE
    )
    cv = StratifiedKFold(n_splits=CV_FOLDS, shuffle=True, random_state=RANDOM_STATE)
    scoring = {
        "f1_macro": "f1_macro",
        "accuracy": "accuracy",
        "balanced_accuracy": "balanced_accuracy",
        "neg_log_loss": "neg_log_loss",
    }

    comparison_rows = []
    fitted_searches: dict[str, GridSearchCV] = {}
    for name, (pipeline, parameters) in candidate_searches().items():
        search = GridSearchCV(
            pipeline,
            parameters,
            scoring=scoring,
            refit="f1_macro",
            cv=cv,
            n_jobs=N_JOBS,
            return_train_score=False,
        )
        search.fit(x_train, y_train)
        fitted_searches[name] = search
        trials = compact_cv_results(search)
        trials.to_csv(REPORTS_DIR / f"hyperparameter_trials_{name}.csv", index=False)
        best = search.best_index_
        comparison_rows.append(
            {
                "model": name,
                "best_parameters": json.dumps(search.best_params_, sort_keys=True),
                "cv_f1_macro_mean": search.cv_results_["mean_test_f1_macro"][best],
                "cv_f1_macro_std": search.cv_results_["std_test_f1_macro"][best],
                "cv_accuracy_mean": search.cv_results_["mean_test_accuracy"][best],
                "cv_balanced_accuracy_mean": search.cv_results_["mean_test_balanced_accuracy"][best],
                "cv_log_loss_mean": -search.cv_results_["mean_test_neg_log_loss"][best],
            }
        )

    comparison = pd.DataFrame(comparison_rows).sort_values(
        ["cv_f1_macro_mean", "cv_log_loss_mean"], ascending=[False, True]
    ).reset_index(drop=True)
    comparison["rank"] = np.arange(1, len(comparison) + 1)
    comparison.to_csv(REPORTS_DIR / "model_comparison.csv", index=False)
    best_name = comparison.loc[0, "model"]
    best_model = fitted_searches[best_name].best_estimator_

    test_rows = []
    for name, search in fitted_searches.items():
        model = search.best_estimator_
        predicted = model.predict(x_test)
        probability = model.predict_proba(x_test)
        metrics = metric_summary(y_test, predicted, probability, class_names)
        test_rows.append({"model": name, **metrics})
        classification_frame(y_test, predicted, class_names).to_csv(REPORTS_DIR / f"classification_report_{name}.csv", index=False)
        confusion_frame(y_test, predicted, class_names).to_csv(REPORTS_DIR / f"confusion_matrix_{name}.csv")
    test_comparison = pd.DataFrame(test_rows).sort_values("f1_macro", ascending=False).reset_index(drop=True)
    test_comparison.to_csv(REPORTS_DIR / "test_model_comparison.csv", index=False)

    final_prediction = best_model.predict(x_test)
    final_probability = best_model.predict_proba(x_test)
    final_metrics = metric_summary(y_test, final_prediction, final_probability, class_names)
    classification_frame(y_test, final_prediction, class_names).to_csv(REPORTS_DIR / "classification_report_best_model.csv", index=False)
    confusion_frame(y_test, final_prediction, class_names).to_csv(REPORTS_DIR / "confusion_matrix_best_model.csv")
    save_confusion_matrix(y_test, final_prediction, class_names, f"Best model: {best_name}", FIGURES_DIR / "confusion_matrix_best_model.png")
    confidence = save_probability_confidence(final_probability, FIGURES_DIR / "prediction_confidence.png")
    confidence.to_csv(REPORTS_DIR / "prediction_confidence.csv", index=False)
    save_permutation_importance(best_model, x_test, y_test)

    baseline = build_baseline(x_train)
    save_baseline(baseline, MODELS_DIR / "monitoring_baseline.json")
    holdout_drift = feature_drift(x_test, baseline)
    holdout_drift.to_csv(MONITORING_DIR / "holdout_feature_drift.csv", index=False)
    prediction_distribution(final_prediction, class_names).to_csv(MONITORING_DIR / "holdout_prediction_distribution.csv", index=False)
    (MONITORING_DIR / "holdout_monitoring_summary.json").write_text(
        json.dumps(monitoring_summary(holdout_drift, len(x_test)), indent=2), encoding="utf-8"
    )

    # Explainability runs in a clean child process. This avoids a Windows cleanup
    # issue when SHAP/Numba is imported after scikit-learn's model search.
    joblib.dump(best_model, MODELS_DIR / "iris_classifier.joblib")
    shap_status = "completed"
    try:
        environment = os.environ.copy()
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "scripts" / "generate_shap.py")],
            check=True,
            timeout=120,
            env=environment,
            capture_output=True,
            text=True,
        )
    except Exception as error:  # Training remains usable if optional explainability fails.
        shap_status = f"failed: {error}"
        (REPORTS_DIR / "shap_summary.md").write_text(
            "# SHAP explanation\n\nSHAP generation failed. "
            f"The fitted model and permutation importance are still available. Error: `{error}`\n",
            encoding="utf-8",
        )

    metadata = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "selected_model": best_name,
        "selection_metric": "mean cross-validation macro F1",
        "best_parameters": fitted_searches[best_name].best_params_,
        "feature_columns": FEATURE_COLUMNS,
        "class_names": class_names,
        "train_rows": len(x_train),
        "test_rows": len(x_test),
        "random_state": RANDOM_STATE,
        "dataset_sha256": dataset_fingerprint(dataset_path),
        "holdout_metrics": final_metrics,
        "shap_status": shap_status,
    }
    (MODELS_DIR / "model_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    summary = {
        "selected_model": best_name,
        "selection_metric": "mean cross-validation macro F1",
        "best_cv_f1_macro": float(comparison.loc[0, "cv_f1_macro_mean"]),
        "holdout_metrics": final_metrics,
        "data_split": {"train_rows": len(x_train), "test_rows": len(x_test), "stratified": True},
        "shap_status": shap_status,
    }
    (REPORTS_DIR / "training_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(
        f"Training complete. Selected {best_name}; hold-out macro F1: {final_metrics['f1_macro']:.3f}. "
        f"Artifacts written to {REPORTS_DIR} and {MODELS_DIR}."
    )
    # sklearn/SHAP dependencies can hang during object teardown on this Windows
    # environment after all artifacts are flushed. This CLI has no state to retain.
    if exit_cleanly_on_windows and sys.platform == "win32":
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(0)


if __name__ == "__main__":
    main(exit_cleanly_on_windows=True)
