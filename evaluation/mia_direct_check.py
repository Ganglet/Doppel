"""
Doppel - Track 2: direct membership check on real generator output, with the holdout confound measured.

Score = -(distance from a row to its nearest synthetic row); AUROC of members vs non-members, no
shadow-model training. Three tables:

  1. Target: generator fit on all 94 train rows, non-members are real holdout rows. Mean AUROC over 20
     seeds with a 95% bootstrap interval that resamples the member and non-member rows (seeds only
     resample the generator, so seed sd understates the uncertainty from 20-35 non-members).
  2. Shift diagnostic: generator fit on a random half of train (47 rows). Members are that half.
     Non-members are (a) the other 47 train rows, which come from the same distribution, versus
     (b) holdout rows. If (b) reads higher than (a), the holdout's distribution shift, not
     membership, is inflating table 1.
  3. Ceiling control: synthetic = exact copy of train.

The holdout has 15 Puerto Rican admissions absent from train, so "non-PR" drops them.

    python -m evaluation.mia_direct_check [--workers N]

Table 1 reads the synthetic files evaluation.eval_runner wrote to output/synthetic/eval/<arm>/, so run the
runner first. The half-train fits in table 2 are done in parallel.
"""

import os

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

import argparse
import json
import subprocess
import warnings
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd
from scipy.stats import rankdata

from evaluation.arms import resolve
from evaluation.eval_runner import real_generator_fn
from evaluation.membership_inference import codes_distances, gower_distances
from generators import schema as S

SEEDS = list(range(42, 62))
ARM_NAMES = ("independent_marginals", "gaussian_copula", "gaussian_copula_shrink025", "ctgan", "tvae")
ATTACKS = {"gower": gower_distances, "icd9_codes": codes_distances}
PUERTO_RICAN = "HISPANIC/LATINO - PUERTO RICAN"
N_BOOT = 1000


def auroc(member_scores, nonmember_scores):
    n1, n2 = len(member_scores), len(nonmember_scores)
    ranks = rankdata(np.r_[member_scores, nonmember_scores])
    return (ranks[:n1].sum() - n1 * (n1 + 1) / 2) / (n1 * n2)


def pooled_scores(row_sets, synth, distance_fn):
    """Score every row set in ONE distance call. gower_distances scales numeric columns by the range of
    the rows it is given, so scoring members and non-members in separate calls puts them on different
    scales and inflates the AUROC (found while writing this script)."""
    pool = pd.concat(row_sets, ignore_index=True)
    scored = -distance_fn(pool, synth).min(axis=1)
    return np.split(scored, np.cumsum([len(r) for r in row_sets])[:-1])


def score_matrices(train, nonmembers, synths, distance_fn):
    mem, non = zip(*[pooled_scores([train, nonmembers], s, distance_fn) for s in synths])
    return np.array(mem), np.array(non)


def mean_auroc(mem, non):
    return float(np.mean([auroc(mem[k], non[k]) for k in range(len(mem))]))


def bootstrap_ci(mem, non, rng):
    reps = []
    for _ in range(N_BOOT):
        i = rng.integers(0, mem.shape[1], mem.shape[1])
        j = rng.integers(0, non.shape[1], non.shape[1])
        reps.append(np.mean([auroc(mem[k, i], non[k, j]) for k in range(len(mem))]))
    return np.percentile(reps, [2.5, 97.5])


def fmt(mean, ci):
    return f"{mean:.3f} [{ci[0]:.3f}, {ci[1]:.3f}]"


def half_train_task(arm, seed):
    """One generator fit on a random 47-row half of train, scored against three non-member sets."""
    real = S.load_real()
    train = real[real[S.SPLIT_COL] == S.TRAIN_SPLIT].reset_index(drop=True)
    holdout = real[real[S.SPLIT_COL] != S.TRAIN_SPLIT].reset_index(drop=True)
    holdout_non_pr = holdout[holdout["ethnicity"] != PUERTO_RICAN].reset_index(drop=True)
    order = np.random.default_rng(seed).permutation(len(train))
    half_a = train.iloc[order[:47]].reset_index(drop=True)
    half_b = train.iloc[order[47:]].reset_index(drop=True)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        synth = real_generator_fn(arm)(half_a, None, len(half_a), seed)
        out = {}
        for name, fn in ATTACKS.items():
            ms, sb, sn, sh = pooled_scores([half_a, half_b, holdout_non_pr, holdout], synth, fn)
            out[name] = (auroc(ms, sb), auroc(ms, sn), auroc(ms, sh))
    return arm, seed, out


def generators_differ(commit_a, commit_b):
    if "unknown" in (commit_a, commit_b):
        return True
    return subprocess.run(["git", "diff", "--quiet", commit_a, commit_b, "--", "generators"]).returncode != 0


def target_synths(arm):
    directory = S.SYNTH_DIR / "eval" / arm
    generator = resolve(arm)[0]  # generators.generate.run names files after the generator, not the arm
    paths = [directory / f"{generator}_seed{s}.csv" for s in SEEDS]
    missing = [str(p) for p in paths if not p.exists()]
    if missing:
        raise SystemExit(f"missing {len(missing)} synthetic files for {arm}; run evaluation.eval_runner first, e.g. {missing[0]}")
    commits = sorted({json.loads(p.with_suffix(".manifest.json").read_text())["git_commit"].removesuffix("-dirty") for p in paths})
    if any(generators_differ(commits[0], other) for other in commits[1:]):
        print(f"   WARNING: {arm} files come from commits {commits} whose generators/ differ; regenerate them together")
    return [S.load_real(p) for p in paths]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument("--workers", type=int, default=max(1, min(12, (os.cpu_count() or 4) - 4)))
    parser.add_argument("--arms", nargs="+", default=list(ARM_NAMES))
    args = parser.parse_args(argv)

    real = S.load_real()
    train = real[real[S.SPLIT_COL] == S.TRAIN_SPLIT].reset_index(drop=True)
    holdout = real[real[S.SPLIT_COL] != S.TRAIN_SPLIT].reset_index(drop=True)
    holdout_non_pr = holdout[holdout["ethnicity"] != PUERTO_RICAN].reset_index(drop=True)
    rng = np.random.default_rng(0)

    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        pending = [pool.submit(half_train_task, arm, seed) for arm in sorted(args.arms, key=lambda a: a != "ctgan") for seed in SEEDS]

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            print("1. Target generator (fit on all 94 train rows), mean AUROC [95% bootstrap interval], 20 seeds")
            print(f"   {'arm':28s} {'attack':11s} {'vs all holdout (35)':>24s} {'vs non-PR holdout (20)':>26s}")
            for arm in args.arms:
                synths = target_synths(arm)
                for name, fn in ATTACKS.items():
                    cells = []
                    for ho in (holdout, holdout_non_pr):
                        mem, non = score_matrices(train, ho, synths, fn)
                        cells.append(fmt(mean_auroc(mem, non), bootstrap_ci(mem, non, rng)))
                    print(f"   {arm:28s} {name:11s} {cells[0]:>24s} {cells[1]:>26s}", flush=True)

            print("\n3. Ceiling control (synthetic = exact copy of train)")
            for name, fn in ATTACKS.items():
                m1, n1 = score_matrices(train, holdout, [train], fn)
                m2, n2 = score_matrices(train, holdout_non_pr, [train], fn)
                print(f"   {name:11s} vs all holdout {mean_auroc(m1, n1):.3f} | vs non-PR holdout {mean_auroc(m2, n2):.3f}")

        results = {}
        for fut in pending:
            arm, seed, out = fut.result()
            results[(arm, seed)] = out

    print("\n2. Shift diagnostic (generator fit on a random 47-row half of train), mean AUROC over 20 seeds")
    print(f"   {'arm':28s} {'attack':11s} {'vs other train half (47)':>26s} {'vs non-PR holdout (20)':>24s} {'vs all holdout (35)':>21s}")
    for arm in args.arms:
        for name in ATTACKS:
            vals = np.array([results[(arm, s)][name] for s in SEEDS])
            print(f"   {arm:28s} {name:11s} {vals[:, 0].mean():>26.3f} {vals[:, 1].mean():>24.3f} {vals[:, 2].mean():>21.3f}")


if __name__ == "__main__":
    main()
