# Iris data profile

## Data quality

- Rows: 150
- Predictor columns: 4
- Missing feature values: 0
- Duplicate full rows: 0
- Identifier treatment: `Id` is retained in the source data but excluded from modelling because it is only a record key.

## Class balance

The data has 3 species with counts: Iris-setosa = 50, Iris-versicolor = 50, Iris-virginica = 50. This is a balanced data set, so accuracy and macro F1 should be similar; macro F1 remains the primary tuning metric so each class has equal weight.

## Patterns worth modelling

- Petal measurements are expected to carry strong discriminatory signal; inspect `figures/pairwise_relationships.png` for the separation between species.
- The strongest absolute feature correlation is between `PetalLengthCm` and `PetalWidthCm`. Regularized and distance-based models are therefore evaluated within preprocessing pipelines.
- IQR flags are descriptive only. Iris is deliberately small, so no row is automatically removed; see `outlier_summary.csv` before deciding that an observation is erroneous.

## Files

The accompanying figures show class balance, distributions by class, within-class spread, correlations, and pairwise relationships. The CSV files provide reproducible numeric summaries.
