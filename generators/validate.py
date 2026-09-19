"""Checks a synthetic CSV against the Stage 2 output contract (docs/A1_generative_modeling.md).

    python -m generators.validate output/synthetic/gaussian_copula_seed42.csv

Every check is against the train split only. A category or code that appears in synthetic output but
never in train can only come from the holdout (leak) or from the generator inventing it.
"""

import argparse
import json
import sys
from collections import Counter

import numpy as np
import pandas as pd

from . import schema as S


def _code_problem(raw, primary, n_diag, train_codes) -> str | None:
    try:
        codes = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return "not valid JSON"
    if not isinstance(codes, list) or not codes or not all(isinstance(c, str) for c in codes):
        return "not a non-empty JSON list of strings"
    if len(set(codes)) != len(codes):
        return "duplicate codes in one admission"
    if codes[0] != primary:
        return "first code differs from icd9_primary"
    if len(codes) != n_diag:
        return "length differs from n_diagnoses"
    if not set(codes) <= train_codes:
        return "code never seen in train"
    return None


def check_contract(synth: pd.DataFrame, real: pd.DataFrame) -> list[str]:
    if list(synth.columns) != list(real.columns):
        missing = sorted(set(real.columns) - set(synth.columns))
        extra = sorted(set(synth.columns) - set(real.columns))
        return [f"columns must match {S.REAL_CSV} in name and order (missing={missing}, extra={extra})"]
    if synth.empty:
        return ["no rows"]

    train = real[real[S.SPLIT_COL] == S.TRAIN_SPLIT]
    errors = []

    kinds = {c: (real[c].dtype.kind, synth[c].dtype.kind) for c in real.columns}
    errors += [f"{c}: dtype kind '{s}' but real is '{r}'" for c, (r, s) in kinds.items() if r != s]

    if not (synth[S.SPLIT_COL] == S.SYNTH_SPLIT).all():
        errors.append(f"split must be '{S.SYNTH_SPLIT}' on every row")
    for c in S.ID_COLS:
        if collide := set(synth[c]) & set(real[c]):
            errors.append(f"{c}: {len(collide)} values collide with real IDs")
    if synth[S.ID_COLS[1]].duplicated().any():
        errors.append(f"{S.ID_COLS[1]} is not unique")

    for c in S.CATEGORICAL:
        if unseen := set(synth[c].astype(str)) - set(train[c].astype(str)):
            errors.append(f"{c}: {len(unseen)} levels never seen in train, e.g. {sorted(unseen)[:3]}")
    for c in S.BINARY:
        if not synth[c].isin([0, 1]).all():
            errors.append(f"{c}: values outside {{0, 1}}")

    age = synth[S.AGE_COL]
    if not age.between(0, S.AGE_CAP).all():
        errors.append(f"{S.AGE_COL}: values outside [0, {S.AGE_CAP}]")
    if (age[synth[S.AGE_FLAG_COL].astype(bool)] != S.AGE_CAP).any():
        errors.append(f"{S.AGE_FLAG_COL} rows must have {S.AGE_COL} == {S.AGE_CAP}")

    for c in S.continuous_cols(real):
        v = synth[c]
        if np.isinf(v).any():
            errors.append(f"{c}: infinite values")
        if v.isna().any() and not train[c].isna().any():
            errors.append(f"{c}: missing values, but this column is never missing in train")
        if (v.dropna() < 0).any():
            errors.append(f"{c}: negative values")
        if c.endswith("_abnormal_frac") and (v.dropna() > 1).any():
            errors.append(f"{c}: fraction above 1")
    for i in S.lab_ids(real):
        mean_c, frac_c = S.lab_pair(i)
        if (synth[mean_c].isna() != synth[frac_c].isna()).any():
            errors.append(f"lab {i}: mean and abnormal_frac must be missing together")

    train_codes = set(train[S.PRIMARY_COL]) | {c for raw in train[S.CODES_COL] for c in json.loads(raw)}
    problems = Counter(
        p for raw, primary, n_diag in zip(synth[S.CODES_COL], synth[S.PRIMARY_COL].astype(str), synth[S.N_DIAG_COL])
        if (p := _code_problem(raw, primary, n_diag, train_codes))
    )
    errors += [f"{S.CODES_COL}: {n} rows with {p}" for p, n in problems.items()]
    return errors


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("path", help="synthetic CSV to check")
    args = parser.parse_args(argv)

    synth = S.load_real(args.path)
    errors = check_contract(synth, S.load_real())
    if errors:
        print(f"FAIL  {args.path}")
        for e in errors:
            print(f"  - {e}")
        return 1
    print(f"PASS  {args.path}  ({len(synth)} rows)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
