"""
Doppel - Track 2: calibration controls for the membership-inference attack.

Runs five attacks (4 numeric columns, Gower over all columns, ICD-9 code sets, and the code sets
split into codes seen once in train vs codes seen at least twice) against
  exact_copy      generator that returns its training rows unchanged (ceiling)
  disjoint_real   generator that returns real holdout rows it never saw (floor)
  independent_marginals, gaussian_copula   the two Track 1 baselines
over 20 seeds, so a generator's score can be read against a known ceiling and floor.

    python mia_calibration.py
"""

import json
import warnings
from collections import Counter
from functools import partial
from pathlib import Path

import numpy as np

from eval_runner import N_SHADOW, real_generator_fn
from generators import schema as S
from membership_inference import NUMERIC_COLS, codes_distances, gower_distances, run_membership_inference

SEEDS = range(42, 62)
OUT_PATH = Path("results/calibration/mia_calibration.json")


def arms(holdout):
    def exact_copy(member_df, numeric_cols, n_samples, seed):
        return member_df.reset_index(drop=True)

    def disjoint_real(member_df, numeric_cols, n_samples, seed):
        return holdout.sample(n=n_samples, replace=True, random_state=seed).reset_index(drop=True)

    return {
        "exact_copy": exact_copy,
        "disjoint_real": disjoint_real,
        "independent_marginals": real_generator_fn("independent_marginals"),
        "gaussian_copula": real_generator_fn("gaussian_copula"),
    }


def main():
    real = S.load_real()
    train = real[real[S.SPLIT_COL] == S.TRAIN_SPLIT].reset_index(drop=True)
    holdout = real[real[S.SPLIT_COL] != S.TRAIN_SPLIT].reset_index(drop=True)

    code_counts = Counter(c for v in train["icd9_codes"] for c in json.loads(v))
    once = {c for c, n in code_counts.items() if n == 1}
    repeated = {c for c, n in code_counts.items() if n > 1}
    attacks = {
        "numeric4": None,
        "gower": gower_distances,
        "icd9_codes": codes_distances,
        "codes_once": partial(codes_distances, keep_codes=once),
        "codes_repeated": partial(codes_distances, keep_codes=repeated),
    }
    print(f"train ICD-9 codes: {len(once)} seen once, {len(repeated)} seen 2+ times")

    results = {}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for arm, fn in arms(holdout).items():
            results[arm] = {attack: [] for attack in attacks}
            for seed in SEEDS:
                for attack, dist in attacks.items():
                    r = run_membership_inference(train, fn, NUMERIC_COLS, n_shadow=N_SHADOW, seed=seed, distance_fn=dist)
                    results[arm][attack].append(r["mean_attack_auroc"])

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps({"seeds": list(SEEDS), "n_shadow": N_SHADOW, "auroc": results}, indent=2) + "\n")

    print(f"{'arm':24s}" + "".join(f"{name:>19s}" for name in attacks))
    for arm, by_attack in results.items():
        cells = [f"{np.mean(v):.3f} +/- {np.std(v, ddof=1):.3f}" for v in by_attack.values()]
        print(f"{arm:24s}" + "".join(f"{c:>19s}" for c in cells))


if __name__ == "__main__":
    main()
