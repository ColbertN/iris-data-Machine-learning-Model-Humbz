"""Export every embedded image from the preserved original notebook.

Jupyter stores plots in cell outputs and attachments rather than as standalone
files. This script extracts those images into reports/figures/notebook_outputs
so they can be reviewed in GitHub and referenced from the project README.
"""

from __future__ import annotations

import base64
import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK_PATH = PROJECT_ROOT / "notebooks" / "iris_modeling_original.ipynb"
OUTPUT_DIR = PROJECT_ROOT / "reports" / "figures" / "notebook_outputs"

CELL_NAMES = {
    9: "missing_value_heatmap",
    14: "original_feature_correlation_heatmap",
    17: "original_feature_histograms",
    18: "original_species_count_plot",
    44: "notebook_embedded_nonfigure_image",
    47: "original_knn_error_rate_curve",
}
IMAGE_EXTENSIONS = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/svg+xml": ".svg",
}
DATA_URI_PATTERN = re.compile(r"data:(image/(?:png|jpeg|jpg));base64,([A-Za-z0-9+/=\r\n]+)", re.IGNORECASE)


def image_bytes(value: str | list[str]) -> bytes:
    """Decode Jupyter's base64 image or plain SVG representation."""
    payload = "".join(value) if isinstance(value, list) else value
    if payload.lstrip().startswith("<svg"):
        return payload.encode("utf-8")
    return base64.b64decode("".join(payload.split()))


def export_notebook_images() -> list[Path]:
    if not NOTEBOOK_PATH.exists():
        raise FileNotFoundError(f"Original notebook is missing: {NOTEBOOK_PATH}")
    notebook = json.loads(NOTEBOOK_PATH.read_text(encoding="utf-8"))
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    saved: list[Path] = []

    def save(stem: str, mime: str, payload: str | list[str]) -> None:
        extension = IMAGE_EXTENSIONS[mime.lower()]
        destination = OUTPUT_DIR / f"{stem}{extension}"
        destination.write_bytes(image_bytes(payload))
        saved.append(destination)

    for cell_index, cell in enumerate(notebook.get("cells", [])):
        cell_name = CELL_NAMES.get(cell_index, f"cell_{cell_index:02d}_image")
        image_outputs = []
        for output in cell.get("outputs", []):
            data = output.get("data", {})
            # Prefer the PNG representation if Jupyter stored more than one format.
            mime = next((name for name in IMAGE_EXTENSIONS if name in data), None)
            if mime:
                image_outputs.append((mime, data[mime]))
        for output_index, (mime, payload) in enumerate(image_outputs, start=1):
            suffix = f"_output_{output_index:02d}" if len(image_outputs) > 1 else ""
            save(f"{cell_name}{suffix}", mime, payload)

        for attachment_name, representations in cell.get("attachments", {}).items():
            mime = next((name for name in IMAGE_EXTENSIONS if name in representations), None)
            if mime:
                attachment_stem = Path(attachment_name).stem.lower().replace(" ", "_")
                save(f"notebook_attachment_{attachment_stem}", mime, representations[mime])

        source = "".join(cell.get("source", []))
        for image_index, match in enumerate(DATA_URI_PATTERN.finditer(source), start=1):
            mime, payload = match.groups()
            save(f"notebook_inline_image_{cell_index:02d}_{image_index:02d}", mime, payload)

    if not saved:
        raise RuntimeError(f"No embedded images were found in {NOTEBOOK_PATH}")
    return saved


def main() -> None:
    files = export_notebook_images()
    print(f"Exported {len(files)} embedded notebook images to {OUTPUT_DIR.relative_to(PROJECT_ROOT)}")
    for path in files:
        print(f"- {path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
