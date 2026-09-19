"""
Doppel - Track 2: direct membership check on the real synthetic files.

Members are the 94 real train rows, non-members are real holdout rows. Score = -(distance from the
row to its nearest synthetic row), AUROC over members vs non-members, no shadow models.

Read the two columns together: the holdout has 15 Puerto Rican admissions that are absent from train,
so "all holdout" mixes membership with distribution shift. "non-PR holdout" removes that confound but
leaves only 20 non-members.

    python mia_direct_check.py
"""

import warnings

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from generators import schema as S
from generators.generate import run
from membership_inference import codes_distances, gower_distances

SEEDS = range(42, 62)
GENERATORS = ("independent_marginals", "gaussian_copula")
ATTACKS = {"gower": gower_distances, "icd9_codes": codes_distances}
PUERTO_RICAN = "HISPANIC/LATINO - PUERTO RICAN"


def direct_auroc(train, nonmembers, synth, distance_fn):
    pool = pd.concat([train, nonmembers], ignore_index=True)
    score = -distance_fn(pool, synth).min(axis=1)
    labels = np.r_[np.ones(len(train)), np.zeros(len(nonmembers))]
    return roc_auc_score(labels, score)


def main():
    real = S.load_real()
    train = real[real[S.SPLIT_COL] == S.TRAIN_SPLIT].reset_index(drop=True)
    holdout = real[real[S.SPLIT_COL] != S.TRAIN_SPLIT].reset_index(drop=True)
    holdout_non_pr = holdout[holdout["ethnicity"] != PUERTO_RICAN].reset_index(drop=True)

    print(f"{'generator':22s} {'attack':11s} {'vs all holdout (35)':>21s} {'vs non-PR holdout (20)':>24s}")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for generator in GENERATORS:
            synths = [pd.read_csv(run(generator, seed), dtype={"icd9_primary": str}) for seed in SEEDS]
            for name, fn in ATTACKS.items():
                all_ho = [direct_auroc(train, holdout, s, fn) for s in synths]
                non_pr = [direct_auroc(train, holdout_non_pr, s, fn) for s in synths]
                print(f"{generator:22s} {name:11s} {np.mean(all_ho):.4f} +/- {np.std(all_ho, ddof=1):.4f}"
                      f"   {np.mean(non_pr):.4f} +/- {np.std(non_pr, ddof=1):.4f}")


if __name__ == "__main__":
    main()
