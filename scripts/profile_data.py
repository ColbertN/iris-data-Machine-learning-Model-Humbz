"""Generate data-quality checks and decision-useful Iris EDA artifacts."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from iris_model.config import FIGURES_DIR, FEATURE_COLUMNS, REPORTS_DIR, TARGET_COLUMN, ensure_output_directories
from iris_model.data import descriptive_columns, load_data


def save_eda_figures(frame: pd.DataFrame) -> None:
    """Create focused plots for balance, separability, distributions, and correlations."""
    sns.set_theme(style="whitegrid", context="notebook")

    figure, axis = plt.subplots(figsize=(7, 4))
    class_counts = frame[TARGET_COLUMN].value_counts().sort_index()
    sns.barplot(x=class_counts.index, y=class_counts.values, hue=class_counts.index, legend=False, ax=axis, palette="deep")
    axis.set_title("Class balance")
    axis.set_xlabel("Species")
    axis.set_ylabel("Samples")
    axis.tick_params(axis="x", rotation=15)
    figure.tight_layout()
    figure.savefig(FIGURES_DIR / "class_balance.png", dpi=180, bbox_inches="tight")
    plt.close(figure)

    long_frame = frame.melt(id_vars=TARGET_COLUMN, value_vars=FEATURE_COLUMNS, var_name="feature", value_name="cm")
    figure, axes = plt.subplots(2, 2, figsize=(11, 7))
    for axis, feature in zip(axes.flat, FEATURE_COLUMNS):
        sns.histplot(data=frame, x=feature, hue=TARGET_COLUMN, kde=True, stat="density", common_norm=False, ax=axis)
        axis.set_title(feature)
    figure.suptitle("Feature distributions by species", y=1.02)
    figure.tight_layout()
    figure.savefig(FIGURES_DIR / "feature_distributions.png", dpi=180, bbox_inches="tight")
    plt.close(figure)

    figure, axis = plt.subplots(figsize=(11, 5))
    sns.boxplot(data=long_frame, x="feature", y="cm", hue=TARGET_COLUMN, ax=axis)
    axis.set_title("Feature spread and possible outliers by species")
    axis.tick_params(axis="x", rotation=15)
    figure.tight_layout()
    figure.savefig(FIGURES_DIR / "feature_boxplots.png", dpi=180, bbox_inches="tight")
    plt.close(figure)

    correlation = frame[FEATURE_COLUMNS].corr()
    figure, axis = plt.subplots(figsize=(7, 5))
    sns.heatmap(correlation, annot=True, fmt=".2f", cmap="vlag", vmin=-1, vmax=1, square=True, ax=axis)
    axis.set_title("Feature correlation")
    figure.tight_layout()
    figure.savefig(FIGURES_DIR / "feature_correlation.png", dpi=180, bbox_inches="tight")
    plt.close(figure)

    pair_plot = sns.pairplot(frame[[*FEATURE_COLUMNS, TARGET_COLUMN]], hue=TARGET_COLUMN, corner=True, diag_kind="hist")
    pair_plot.figure.suptitle("Pairwise class separability", y=1.02)
    pair_plot.figure.savefig(FIGURES_DIR / "pairwise_relationships.png", dpi=160, bbox_inches="tight")
    plt.close(pair_plot.figure)


def iqr_outlier_summary(frame: pd.DataFrame) -> pd.DataFrame:
    """Flag values outside 1.5 IQR, a transparent descriptive—not deletion—check."""
    rows = []
    for feature in FEATURE_COLUMNS:
        first, third = frame[feature].quantile([0.25, 0.75])
        iqr = third - first
        lower, upper = first - 1.5 * iqr, third + 1.5 * iqr
        flagged = (frame[feature] < lower) | (frame[feature] > upper)
        rows.append(
            {
                "feature": feature,
                "lower_iqr_fence": lower,
                "upper_iqr_fence": upper,
                "flagged_rows": int(flagged.sum()),
                "flagged_rate": float(flagged.mean()),
            }
        )
    return pd.DataFrame(rows)


def write_profile(frame: pd.DataFrame) -> None:
    """Write tabular and narrative EDA outputs."""
    frame[descriptive_columns(frame)].describe(include="all").transpose().to_csv(REPORTS_DIR / "dataset_summary.csv")
    frame[FEATURE_COLUMNS].describe().transpose().to_csv(REPORTS_DIR / "feature_summary.csv")
    frame.groupby(TARGET_COLUMN)[FEATURE_COLUMNS].agg(["mean", "median", "std", "min", "max"]).transpose().to_csv(
        REPORTS_DIR / "class_feature_summary.csv"
    )
    outliers = iqr_outlier_summary(frame)
    outliers.to_csv(REPORTS_DIR / "outlier_summary.csv", index=False)
    counts = frame[TARGET_COLUMN].value_counts().sort_index()
    duplicates = int(frame.duplicated().sum())
    strongest_pair = (
        frame[FEATURE_COLUMNS].corr().abs().where(lambda data: ~data.eq(1)).stack().sort_values(ascending=False).index[0]
    )
    text = f"""# Iris data profile

## Data quality

- Rows: {len(frame)}
- Predictor columns: {len(FEATURE_COLUMNS)}
- Missing feature values: {int(frame[FEATURE_COLUMNS].isna().sum().sum())}
- Duplicate full rows: {duplicates}
- Identifier treatment: `Id` is retained in the source data but excluded from modelling because it is only a record key.

## Class balance

The data has {len(counts)} species with counts: {", ".join(f"{label} = {count}" for label, count in counts.items())}. This is a balanced data set, so accuracy and macro F1 should be similar; macro F1 remains the primary tuning metric so each class has equal weight.

## Patterns worth modelling

- Petal measurements are expected to carry strong discriminatory signal; inspect `figures/pairwise_relationships.png` for the separation between species.
- The strongest absolute feature correlation is between `{strongest_pair[0]}` and `{strongest_pair[1]}`. Regularized and distance-based models are therefore evaluated within preprocessing pipelines.
- IQR flags are descriptive only. Iris is deliberately small, so no row is automatically removed; see `outlier_summary.csv` before deciding that an observation is erroneous.

## Files

The accompanying figures show class balance, distributions by class, within-class spread, correlations, and pairwise relationships. The CSV files provide reproducible numeric summaries.
"""
    (REPORTS_DIR / "data_profile.md").write_text(text, encoding="utf-8")


def main() -> None:
    ensure_output_directories()
    data = load_data()
    write_profile(data)
    save_eda_figures(data)
    print(f"EDA complete. Reports written to {REPORTS_DIR}")


if __name__ == "__main__":
    main()
