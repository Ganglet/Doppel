"""Hyperparameter sweep scored inside train only: memorization (DCR) and fidelity, over patient folds and seeds.

    python -m generators.sweep                            # full default grid
    python -m generators.sweep --only ctgan tvae --seeds 0 1 2 --workers 6

Each (config, seed, fold) is an independent task run in its own process. Fidelity is Track 2's
run_fidelity_report against the fold's fit rows; memorization is diagnostics.dcr_* against the fold's
unseen reference rows. The holdout is never read. Writes output/sweeps/sweep_<utc>.csv (one row per config
and seed) and _summary.csv (mean and sd over seeds per config, ADR-012).
"""

import argparse
import json
import os
import sys
import time
import warnings
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from . import schema as S
from .diagnostics import dcr_distances, dcr_summary, patient_folds
from .generate import GENERATORS, synthesize

SWEEP_DIR = Path("output/sweeps")

GRID = {
    "independent_marginals": [{}],
    "gaussian_copula": [{}] + [{"shrinkage": s} for s in (0.25, 0.5, 0.9)],
    "ctgan": [{"epochs": e} for e in (300, 1000, 3000)],
    "tvae": [{"epochs": e} for e in (300, 1000, 3000)],
}


def _quiet():
    warnings.filterwarnings("ignore")


def _run_task(generator: str, params: dict, seed: int, fold: int, k: int, min_count: int) -> dict:
    from evaluation.fidelity_metrics import run_fidelity_report  # Track 2's metric, unchanged

    real = S.load_real()
    train = real[real[S.SPLIT_COL] == S.TRAIN_SPLIT].reset_index(drop=True)
    fit, ref = list(patient_folds(train, k))[fold]

    start = time.time()
    _, _, synth = synthesize(fit, generator, seed * 100 + fold, params, min_count=min_count)
    seconds = time.time() - start
    synth_d, ref_d = dcr_distances(fit, ref, synth, min_count)
    fidelity = run_fidelity_report(fit, synth)
    return {
        "generator": generator, "params": json.dumps(params, sort_keys=True), "seed": seed, "fold": fold,
        "synth_d": synth_d, "ref_d": ref_d, "seconds": seconds,
        "mean_js": fidelity["mean_js_divergence"], "corr_diff": fidelity["correlation_diff"],
    }


def _cost(task: tuple) -> float:
    generator, params = task[0], task[1]
    return params.get("epochs", 0) * (3 if generator == "ctgan" else 1)


def aggregate(results: list[dict]) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    frame = pd.DataFrame(results)
    for (generator, params, seed), g in frame.groupby(["generator", "params", "seed"], sort=False):
        rows.append({
            "generator": generator, "params": params, "seed": seed,
            **dcr_summary(np.concatenate(g["synth_d"].tolist()), np.concatenate(g["ref_d"].tolist())),
            "mean_js": g["mean_js"].mean(), "corr_diff": g["corr_diff"].mean(),
            "fit_seconds": g["seconds"].sum(),
        })
    per_seed = pd.DataFrame(rows).sort_values(["generator", "params", "seed"]).reset_index(drop=True)
    metrics = ["dcr_ratio", "near_copy_rate", "mean_js", "corr_diff"]
    summary = per_seed.groupby(["generator", "params"])[metrics].agg(["mean", "std"])
    summary.columns = [f"{m}_{stat}" for m, stat in summary.columns]
    summary["seeds"] = per_seed.groupby(["generator", "params"]).size()
    return per_seed, summary.reset_index()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--only", nargs="+", choices=sorted(GRID), default=sorted(GRID))
    parser.add_argument("--seeds", nargs="+", type=int, default=[0, 1, 2])
    parser.add_argument("--folds", type=int, default=5)
    parser.add_argument("--min-count", type=int, default=5)
    parser.add_argument("--workers", type=int, default=max(1, min(6, (os.cpu_count() or 2) - 2)))
    args = parser.parse_args(argv)
    assert set(GRID) <= set(GENERATORS)

    # Workers are spawned fresh, so this reaches numpy's BLAS before it loads.
    for var in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
        os.environ[var] = "1"

    tasks = [(g, p, s, f, args.folds, args.min_count)
             for g in args.only for p in GRID[g] for s in args.seeds for f in range(args.folds)]
    tasks.sort(key=_cost, reverse=True)  # longest first, for load balance
    print(f"{len(tasks)} tasks on {args.workers} workers", flush=True)

    results, start = [], time.time()
    with ProcessPoolExecutor(max_workers=args.workers, initializer=_quiet) as pool:
        futures = {pool.submit(_run_task, *t): t for t in tasks}
        for i, fut in enumerate(as_completed(futures), 1):
            r = fut.result()
            results.append(r)
            print(f"[{i:3d}/{len(tasks)}] {time.time() - start:6.0f}s  {r['generator']:22s} {r['params']:18s} "
                  f"seed={r['seed']} fold={r['fold']}  fit {r['seconds']:5.1f}s", flush=True)

    per_seed, summary = aggregate(results)
    SWEEP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    per_seed.to_csv(SWEEP_DIR / f"sweep_{stamp}.csv", index=False)
    summary.to_csv(SWEEP_DIR / f"sweep_{stamp}_summary.csv", index=False)

    with pd.option_context("display.width", 200, "display.max_columns", None, "display.float_format", "{:.3f}".format):
        print(summary.to_string(index=False))
    print(f"\nwrote {SWEEP_DIR}/sweep_{stamp}.csv and _summary.csv  ({time.time() - start:.0f}s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
