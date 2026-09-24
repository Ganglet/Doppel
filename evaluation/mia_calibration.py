"""
Doppel - Track 2: calibration controls and the positive control for the membership-inference attack.

Runs five attacks (4 numeric columns, Gower over all columns, ICD-9 code sets, and the code sets
split into codes seen once in train vs codes seen at least twice) against
  exact_copy        generator that returns its training rows unchanged (ceiling)
  disjoint_real     generator that returns real holdout rows it never saw (floor)
  tvae              a real generator Track 1 verified memorizes (positive control, ADR-024)
  the other Track 2 arms in evaluation/arms.py
over 20 seeds. Also reports the pooled true-positive rate at 5% and 1% false-positive rate, and which
train records the ICD-9 attack finds easiest to identify.

    python -m evaluation.mia_calibration [--workers N] [--arms A B ...] [--n-seeds N]

Neural arms need the ctgan extras (generators/requirements-neural.txt).
"""

import os

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

import argparse
import json
import warnings
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from functools import partial
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

from evaluation.eval_runner import N_SHADOW, cached, real_generator_fn
from evaluation.membership_inference import NUMERIC_COLS, codes_distances, gower_distances, run_membership_inference
from generators import schema as S

SEEDS = list(range(42, 62))
OUT_PATH = Path("results/calibration/mia_calibration.json")
ARM_NAMES = ["exact_copy", "disjoint_real", "independent_marginals", "gaussian_copula",
             "gaussian_copula_shrink025", "ctgan", "tvae"]
RECORD_ATTACK = "icd9_codes"


def load_context():
    real = S.load_real()
    train = real[real[S.SPLIT_COL] == S.TRAIN_SPLIT].reset_index(drop=True)
    holdout = real[real[S.SPLIT_COL] != S.TRAIN_SPLIT].reset_index(drop=True)
    counts = Counter(c for v in train["icd9_codes"] for c in json.loads(v))
    once = {c for c, n in counts.items() if n == 1}
    repeated = {c for c, n in counts.items() if n > 1}
    return train, holdout, once, repeated


def build_generator(arm, holdout):
    if arm == "exact_copy":
        return lambda member_df, numeric_cols, n_samples, seed: member_df.reset_index(drop=True)
    if arm == "disjoint_real":
        return lambda member_df, numeric_cols, n_samples, seed: holdout.sample(
            n=n_samples, replace=True, random_state=seed).reset_index(drop=True)
    return real_generator_fn(arm)


def calibrate_one(arm, seed):
    train, holdout, once, repeated = load_context()
    attacks = {
        "numeric4": None,
        "gower": gower_distances,
        "icd9_codes": codes_distances,
        "codes_once": partial(codes_distances, keep_codes=once),
        "codes_repeated": partial(codes_distances, keep_codes=repeated),
    }
    generator_fn = cached(build_generator(arm, holdout))
    out, advantage = {}, None
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for name, distance_fn in attacks.items():
            r = run_membership_inference(train, generator_fn, NUMERIC_COLS, n_shadow=N_SHADOW, seed=seed,
                                         distance_fn=distance_fn, return_records=(name == RECORD_ATTACK))
            out[name] = {"auroc": r["mean_attack_auroc"], "tpr_5": r["tpr_at_fpr_5pct"], "tpr_1": r["tpr_at_fpr_1pct"]}
            if name == RECORD_ATTACK:
                advantage = r["record_advantage"]
    return arm, seed, out, advantage


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument("--workers", type=int, default=max(1, min(12, (os.cpu_count() or 4) - 4)))
    parser.add_argument("--arms", nargs="+", default=ARM_NAMES)
    parser.add_argument("--n-seeds", type=int, default=len(SEEDS))
    parser.add_argument("--out", type=Path, default=OUT_PATH)
    args = parser.parse_args(argv)
    seeds = SEEDS[: args.n_seeds]

    train, _, once, repeated = load_context()
    print(f"train ICD-9 codes: {len(once)} seen once, {len(repeated)} seen 2+ times; {args.workers} workers", flush=True)

    slow_first = sorted(args.arms, key=lambda a: -{"ctgan": 3, "tvae": 2}.get(a, 0))
    tasks = [(arm, seed) for arm in slow_first for seed in seeds]
    done = {}
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(calibrate_one, arm, seed) for arm, seed in tasks]
        for i, fut in enumerate(as_completed(futures), 1):
            arm, seed, out, advantage = fut.result()
            done[(arm, seed)] = (out, advantage)
            if i % 10 == 0 or i == len(tasks):
                print(f"  {i}/{len(tasks)} tasks done", flush=True)

    attack_names = list(next(iter(done.values()))[0])
    auroc = {a: {n: [done[(a, s)][0][n]["auroc"] for s in seeds] for n in attack_names} for a in args.arms}
    tpr5 = {a: {n: [done[(a, s)][0][n]["tpr_5"] for s in seeds] for n in attack_names} for a in args.arms}
    tpr1 = {a: {n: [done[(a, s)][0][n]["tpr_1"] for s in seeds] for n in attack_names} for a in args.arms}

    singleton = [sum(1 for c in json.loads(v) if c in once) for v in train["icd9_codes"]]
    record_mean = {a: np.nanmean([done[(a, s)][1] for s in seeds], axis=0) for a in args.arms}

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps({
        "seeds": seeds, "n_shadow": N_SHADOW, "auroc": auroc,
        "tpr_at_fpr_5pct": tpr5, "tpr_at_fpr_1pct": tpr1,
        "record_advantage_mean": {a: v.tolist() for a, v in record_mean.items()},
        "singleton_codes_per_record": singleton,
    }, indent=2) + "\n")

    def table(title, data, fmt="{:.3f}"):
        print(f"\n{title}")
        print(f"{'arm':28s}" + "".join(f"{n:>17s}" for n in attack_names))
        for arm in args.arms:
            cells = [f"{fmt.format(np.mean(v))} +/- {fmt.format(np.std(v, ddof=1))}" for v in data[arm].values()]
            print(f"{arm:28s}" + "".join(f"{c:>17s}" for c in cells))

    table("Mean shadow-model AUROC +/- sd over seeds", auroc)
    table("Pooled TPR at 5% FPR (chance 0.05)", tpr5)
    table("Pooled TPR at 1% FPR (chance 0.01)", tpr1)

    print(f"\nPer-record advantage of the {RECORD_ATTACK} attack (mean over seeds), vs singleton codes per record")
    print(f"{'arm':28s} {'spearman':>9s} {'top-10% singleton codes':>25s} {'rest':>7s}")
    order_all = np.array(singleton)
    for arm in args.arms:
        adv = record_mean[arm]
        ok = ~np.isnan(adv)
        rho = spearmanr(adv[ok], order_all[ok])[0] if ok.sum() > 2 else float("nan")
        cut = np.nanpercentile(adv, 90)
        top = ok & (adv >= cut)
        print(f"{arm:28s} {rho:9.3f} {order_all[top].mean():25.2f} {order_all[ok & ~top].mean():7.2f}")


if __name__ == "__main__":
    main()
