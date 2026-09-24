"""
Doppel - Track 2: how many distinct training rows does each arm's synthetic data sit closest to?

For each synthetic row, find its nearest real train row (Gower distance over all columns). A generator that
collapses onto a few training rows has synthetic rows nearest to few distinct train rows, and a single train
row can be the nearest neighbour of many synthetic rows. Reads the files written by evaluation.eval_runner.

    python -m evaluation.synthetic_coverage
"""

import warnings

import numpy as np

from evaluation.arms import resolve
from evaluation.membership_inference import gower_distances
from generators import schema as S

SEEDS = range(42, 62)
ARM_NAMES = ("independent_marginals", "gaussian_copula", "gaussian_copula_shrink025", "ctgan", "tvae")


def main():
    real = S.load_real()
    train = real[real[S.SPLIT_COL] == S.TRAIN_SPLIT].reset_index(drop=True)
    print(f"{'arm':28s} {'distinct train rows hit (of 94)':>32s} {'max synthetic rows on one train row':>38s}")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for arm in ARM_NAMES:
            generator = resolve(arm)[0]
            distinct, most = [], []
            for seed in SEEDS:
                synth = S.load_real(S.SYNTH_DIR / "eval" / arm / f"{generator}_seed{seed}.csv")
                nearest = gower_distances(train, synth).argmin(axis=0)
                counts = np.bincount(nearest, minlength=len(train))
                distinct.append((counts > 0).sum())
                most.append(counts.max())
            print(f"{arm:28s} {np.mean(distinct):>20.1f} +/- {np.std(distinct, ddof=1):4.1f} {np.mean(most):>25.1f} +/- {np.std(most, ddof=1):4.1f}")


if __name__ == "__main__":
    main()
