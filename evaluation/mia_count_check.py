"""
Doppel - Track 2: does a neighbourhood-count feature make the membership attack stronger?

The baseline attack scores a record by its nearest and 3-nearest synthetic distances. This adds a third
feature, the number of synthetic rows closer than the 5th percentile of all record-to-synthetic distances
in that shadow world, which targets a generator that collapses onto a few training rows (an idea from the
Monte Carlo attack of Hilprecht et al. 2019, as I understand it). Shadow generators are fitted once per
seed and reused for every variant.

    python -m evaluation.mia_count_check [--arms A B ...] [--seeds 42 43 44]
"""

import argparse
import warnings

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

from evaluation.eval_runner import N_SHADOW, real_generator_fn
from evaluation.membership_inference import codes_distances, gower_distances
from generators import schema as S

DISTANCES = {"gower": gower_distances, "icd9_codes": codes_distances}


def shadow_worlds(train, arm, seed):
    generator_fn = real_generator_fn(arm)
    rng = np.random.default_rng(seed)
    n = len(train)
    worlds = []
    for k in range(N_SHADOW):
        members = np.sort(rng.choice(n, size=n // 2, replace=False))
        synth = generator_fn(train.iloc[members], None, len(members), seed + k)
        worlds.append((set(members.tolist()), synth))
    return worlds


def features(matrix, with_count):
    ordered = np.sort(matrix, axis=1)
    cols = [ordered[:, 0], ordered[:, :3].mean(axis=1)]
    if with_count:
        cols.append((matrix < np.percentile(matrix, 5)).sum(axis=1))
    return np.column_stack(cols)


def leave_one_shadow_out_auroc(train, worlds, distance_fn, with_count):
    n = len(train)
    X, y, g = [], [], []
    for k, (members, synth) in enumerate(worlds):
        X.append(features(distance_fn(train, synth), with_count))
        y.append(np.array([i in members for i in range(n)], dtype=int))
        g.append(np.full(n, k))
    X, y, g = map(np.concatenate, (X, y, g))
    aucs = []
    for k in np.unique(g):
        model = LogisticRegression(max_iter=1000).fit(X[g != k], y[g != k])
        aucs.append(roc_auc_score(y[g == k], model.predict_proba(X[g == k])[:, 1]))
    return float(np.mean(aucs))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument("--arms", nargs="+", default=["gaussian_copula", "tvae"])
    parser.add_argument("--seeds", nargs="+", type=int, default=[42, 43, 44])
    args = parser.parse_args(argv)

    real = S.load_real()
    train = real[real[S.SPLIT_COL] == S.TRAIN_SPLIT].reset_index(drop=True)

    print(f"{'arm':28s} {'distance':11s} {'min + knn3':>11s} {'+ count':>9s}   (mean AUROC over {len(args.seeds)} seeds)")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for arm in args.arms:
            worlds = {seed: shadow_worlds(train, arm, seed) for seed in args.seeds}
            for name, fn in DISTANCES.items():
                base = np.mean([leave_one_shadow_out_auroc(train, worlds[s], fn, False) for s in args.seeds])
                counted = np.mean([leave_one_shadow_out_auroc(train, worlds[s], fn, True) for s in args.seeds])
                print(f"{arm:28s} {name:11s} {base:11.3f} {counted:9.3f}", flush=True)


if __name__ == "__main__":
    main()
