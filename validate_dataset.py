"""
Doppel — Track 3, Phase 2: data validation checks.

Validates output/mimic_demo_clean.csv against:
1. contracts/schemas/dataset.schema.json (via the generated manifest)
2. Expected columns from schema_and_feature_dictionary.md
3. Known/documented null patterns (labs may be null, ID/label columns may not)
4. Basic sanity bounds (age 0-89, split values, no negative LOS)

Exits non-zero on failure so this can gate a CI step or K8s Job.

Run after preprocess_mimic_demo.py and generate_manifest.py:
    python validate_dataset.py
"""

import json
import os
import sys
import pandas as pd
from pathlib import Path

try:
    import jsonschema
except ImportError:
    print("ERROR: jsonschema not installed. pip install jsonschema", file=sys.stderr)
    sys.exit(1)

OUT_DIR = Path(os.environ.get("OUT_DIR", "./output"))
CSV_PATH = OUT_DIR / "mimic_demo_clean.csv"
MANIFEST_PATH = OUT_DIR / "mimic_demo_clean.manifest.json"
CONTRACT_SCHEMA_PATH = Path("./contracts/schemas/dataset.schema.json")

# Columns that must never be null (identifiers, labels, core demographics).
# Lab columns are expected to have nulls on a sparse 100-patient demo and
# are intentionally excluded here — see schema_and_feature_dictionary.md §5.
REQUIRED_NON_NULL_COLUMNS = [
    "subject_id", "hadm_id", "admission_type", "ethnicity",
    "hospital_expire_flag", "los_hospital_days", "age", "gender",
    "n_diagnoses", "icd9_codes", "readmit_30d", "split",
]

EXPECTED_SPLIT_VALUES = {"train", "holdout"}


def check(condition, message, errors):
    if not condition:
        errors.append(message)


def validate_contract_schema(errors):
    if not CONTRACT_SCHEMA_PATH.exists():
        errors.append(f"Contract schema not found at {CONTRACT_SCHEMA_PATH} — skipping contract check")
        return
    if not MANIFEST_PATH.exists():
        errors.append(f"Manifest not found at {MANIFEST_PATH} — run generate_manifest.py first")
        return

    schema = json.loads(CONTRACT_SCHEMA_PATH.read_text())
    manifest = json.loads(MANIFEST_PATH.read_text())
    try:
        jsonschema.validate(manifest, schema)
    except jsonschema.ValidationError as e:
        errors.append(f"Manifest fails contract schema: {e.message}")


def validate_required_columns(df, errors):
    missing = [c for c in REQUIRED_NON_NULL_COLUMNS if c not in df.columns]
    check(not missing, f"Missing required columns: {missing}", errors)


def validate_no_unexpected_nulls(df, errors):
    for col in REQUIRED_NON_NULL_COLUMNS:
        if col not in df.columns:
            continue
        n_null = df[col].isnull().sum()
        check(n_null == 0, f"Column '{col}' has {n_null} unexpected null(s) — this column must never be null", errors)


def validate_icd9_codes_json(df, errors):
    bad = 0
    for v in df["icd9_codes"].dropna():
        try:
            json.loads(v)
        except (json.JSONDecodeError, TypeError):
            bad += 1
    check(bad == 0, f"{bad} row(s) in icd9_codes fail json.loads() — must be valid JSON per ADR-004", errors)


def validate_split_values(df, errors):
    actual = set(df["split"].dropna().unique())
    check(
        actual.issubset(EXPECTED_SPLIT_VALUES),
        f"Unexpected split values: {actual - EXPECTED_SPLIT_VALUES}",
        errors,
    )
    check("train" in actual and "holdout" in actual, "split column must contain both 'train' and 'holdout'", errors)


def validate_no_subject_leakage(df, errors):
    leak = df.groupby("subject_id")["split"].nunique()
    leaking_subjects = leak[leak > 1]
    check(
        len(leaking_subjects) == 0,
        f"{len(leaking_subjects)} subject_id(s) appear in both train and holdout — split leakage",
        errors,
    )


def validate_sanity_bounds(df, errors):
    check((df["age"] >= 0).all() and (df["age"] <= 89).all(), "age out of expected [0, 89] bounds", errors)
    check((df["los_hospital_days"] >= 0).all(), "los_hospital_days has negative values", errors)
    check(df["hospital_expire_flag"].isin([0, 1]).all(), "hospital_expire_flag has non-binary values", errors)
    check(df["readmit_30d"].isin([0, 1]).all(), "readmit_30d has non-binary values", errors)


def main():
    errors = []

    if not CSV_PATH.exists():
        print(f"FAIL: {CSV_PATH} not found — run preprocess_mimic_demo.py first", file=sys.stderr)
        sys.exit(1)

    df = pd.read_csv(CSV_PATH)

    validate_contract_schema(errors)
    validate_required_columns(df, errors)
    if not errors:
        validate_no_unexpected_nulls(df, errors)
        validate_icd9_codes_json(df, errors)
        validate_split_values(df, errors)
        validate_no_subject_leakage(df, errors)
        validate_sanity_bounds(df, errors)

    if errors:
        print(f"VALIDATION FAILED — {len(errors)} issue(s):", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        sys.exit(1)
    else:
        print(f"VALIDATION PASSED — {len(df)} rows, {len(df.columns)} columns, all checks green.")
        sys.exit(0)


if __name__ == "__main__":
    main()