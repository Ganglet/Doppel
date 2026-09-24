"""
Doppel - export the generated synthetic datasets for the web dashboard's Data section.

The Streamlit dashboard lets you pick a generated CSV and shows its size, a preview, the column types and the
generator manifest. This writes the same things for every evaluated dataset (5 generators x 20 seeds under
output/synthetic/eval/), one small JSON file per dataset, so the page can load a table when you pick one.

    python web/scripts/export_datasets.py

The output goes to web/public/data/datasets/ and is git-ignored, like output/synthetic/ itself.
"""

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "output" / "synthetic" / "eval"
OUT = ROOT / "web" / "public" / "data" / "datasets"

LABELS = {
    "independent_marginals": "Independent marginals",
    "gaussian_copula": "Gaussian copula",
    "gaussian_copula_shrink025": "Gaussian copula, shrink 0.25",
    "ctgan": "CTGAN",
    "tvae": "TVAE",
}


def parse(cell):
    """Empty -> None, True/False -> bool, whole number -> int, other number -> float, anything else stays text."""
    if cell == "":
        return None
    if cell in ("True", "False"):
        return cell == "True"
    try:
        return int(cell)
    except ValueError:
        pass
    try:
        return float(cell)
    except ValueError:
        return cell


def dtype_of(values):
    """Name the column type the way pandas would: int64, float64 or object."""
    present = [v for v in values if v is not None]
    if not present:
        return "float64"
    if all(isinstance(v, bool) for v in present):
        return "bool" if len(present) == len(values) else "object"
    if any(isinstance(v, (str, bool)) for v in present):
        return "object"
    if any(isinstance(v, float) for v in present) or len(present) < len(values):
        return "float64"
    return "int64"


def export_one(csv_path):
    with open(csv_path, newline="", encoding="utf-8") as fh:
        reader = csv.reader(fh)
        header = next(reader)
        rows = [[parse(c) for c in r] for r in reader]
    cols = list(zip(*rows)) if rows else [() for _ in header]
    info = [
        {"name": h, "dtype": dtype_of(list(c)), "missing": sum(v is None for v in c)}
        for h, c in zip(header, cols)
    ]
    manifest_path = csv_path.with_suffix(".manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else None
    return {
        "file": csv_path.name,
        "n_rows": len(rows),
        "n_cols": len(header),
        "missing": sum(i["missing"] for i in info),
        "columns": info,
        "rows": rows,
        "manifest": manifest,
    }


def main():
    if not SRC.exists():
        sys.exit(f"{SRC} does not exist. Generate the evaluation datasets first (see docs/B3).")
    OUT.mkdir(parents=True, exist_ok=True)
    index = []
    for arm, label in LABELS.items():
        files = sorted((SRC / arm).glob("*_seed*.csv"), key=lambda p: int(p.stem.rsplit("seed", 1)[1]))
        seeds = []
        for f in files:
            seed = int(f.stem.rsplit("seed", 1)[1])
            (OUT / f"{arm}_seed{seed}.json").write_text(
                json.dumps(export_one(f), separators=(",", ":")), encoding="utf-8"
            )
            seeds.append(seed)
        if seeds:
            index.append({"id": arm, "label": label, "seeds": seeds})
    (OUT / "index.json").write_text(json.dumps({"arms": index}, indent=1), encoding="utf-8")
    total = sum(len(a["seeds"]) for a in index)
    print(f"wrote {total} datasets for {len(index)} generators to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
