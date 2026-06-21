"""Central project paths and modelling constants."""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_CANDIDATES = (PROJECT_ROOT / "Iris.csv", PROJECT_ROOT / "data" / "Iris.csv")
MODELS_DIR = PROJECT_ROOT / "models"
REPORTS_DIR = PROJECT_ROOT / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"
MONITORING_DIR = REPORTS_DIR / "monitoring"

TARGET_COLUMN = "Species"
ID_COLUMN = "Id"
FEATURE_COLUMNS = ["SepalLengthCm", "SepalWidthCm", "PetalLengthCm", "PetalWidthCm"]
RANDOM_STATE = 42
TEST_SIZE = 0.20
CV_FOLDS = 5
# Small data set; one process avoids unnecessary process-spawn issues on Windows.
N_JOBS = 1


def ensure_output_directories() -> None:
    """Create output folders used by scripts, including empty-project cases."""
    for directory in (MODELS_DIR, REPORTS_DIR, FIGURES_DIR, MONITORING_DIR):
        directory.mkdir(parents=True, exist_ok=True)
