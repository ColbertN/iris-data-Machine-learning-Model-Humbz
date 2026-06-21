# Iris classification project

This project turns the original I0ris notebook into a reproducible modelling workflow. It profiles the data, tunes multiple pipelines using cross-validation, selects and evaluates a model on a hold-out set, produces SHAP explanations, and writes data-drift monitoring and scoring outputs.

## Project layout

- `notebooks/iris_modeling.ipynb` — a guided notebook that runs the workflow and reads the reports.
- `notebooks/iris_modeling_original.ipynb` — the original notebook, moved here unchanged for reference.
- `scripts/` — command-line entry points for profiling, training, and scoring.
- `src/iris_model/` — reusable, testable workflow code.
- `models/` — saved fitted model and its metadata after training.
- `reports/figures/` — EDA, evaluation, and SHAP plots.
- `reports/monitoring/` — feature-drift and prediction-distribution reports.

## Run the workflow

From the project root:

```powershell
python scripts/profile_data.py
python scripts/train_compare.py
python scripts/score_model.py --input Iris.csv
```

The scoring command accepts a CSV containing the four measurement columns. If a `Species` column is present, it also writes labelled performance metrics. The last command scores the supplied Iris data only to demonstrate the scoring and monitoring flow; use a genuinely new batch in production.

## Modelling design

- The non-predictive `Id` field is excluded from training.
- The data is split once into stratified 80% training and 20% untouched test sets.
- Logistic Regression, KNN, Random Forest, and SVM pipelines are tuned with stratified 5-fold cross-validation on the training set only.
- Selection uses mean cross-validation macro F1, which treats all three species evenly; accuracy, balanced accuracy, log loss, and class-level reports are also retained.
- The saved model includes preprocessing in its pipeline, preventing train/score scaling mismatch.

The Iris data set is very small (150 rows), so performance estimates naturally have uncertainty. The cross-validation and untouched test split make the comparison more trustworthy than fitting and evaluating on the same data, but this is still an educational model rather than a production-ready scientific classifier.
