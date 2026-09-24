"""
Doppel — Track 3, Phase 2: dataset manifest generator.

Produces output/mimic_demo_clean.manifest.json, describing
output/mimic_demo_clean.csv per contracts/schemas/dataset.schema.json.
This is the metadata file Track 1/2 can read to know what columns
exist and their types without opening the CSV.

Run after preprocess_mimic_demo.py:
    python generate_manifest.py
"""

import json
import os
import subprocess
import pandas as pd
from pathlib import Path

OUT_DIR = Path(os.environ.get("OUT_DIR", "./output"))
CSV_PATH = OUT_DIR / "mimic_demo_clean.csv"
MANIFEST_PATH = OUT_DIR / "mimic_demo_clean.manifest.json"

SCHEMA_VERSION = "1.0"

# pandas dtype -> a small set of contract-friendly type names
DTYPE_MAP = {
    "int64": "integer",
    "Int64": "integer",
    "float64": "float",
    "bool": "boolean",
    "object": "string",
}


def pandas_dtype_to_contract_dtype(dtype_str: str) -> str:
    return DTYPE_MAP.get(dtype_str, "string")


def get_git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True
        ).strip()
    except Exception:
        return "unknown"


def main():
    df = pd.read_csv(CSV_PATH)

    columns = []
    for col in df.columns:
        dtype_str = str(df[col].dtype)
        columns.append({
            "name": col,
            "dtype": pandas_dtype_to_contract_dtype(dtype_str),
            "nullable": bool(df[col].isnull().any()),
        })

    manifest = {
        "dataset_id": "mimic_demo_clean",
        "schema_version": SCHEMA_VERSION,
        "data_path": "output/mimic_demo_clean.csv",
        "format": "csv",
        "columns": columns,
    }

    with open(MANIFEST_PATH, "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"Wrote manifest for {len(df)} rows, {len(columns)} columns -> {MANIFEST_PATH}")


if __name__ == "__main__":
    main()