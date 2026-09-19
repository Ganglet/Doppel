"""
Doppel - Track 2: fidelity / utility / privacy Pareto frontier over generators.

Reads every results/<generator>_seed<n>.json and reduces each generator to three numbers per seed:

  fidelity   mean JS divergence vs real train                    (lower is better)
  utility    mean of the two TSTR AUROCs (LR and random forest)  (higher is better)
  privacy    worst-case membership AUROC over the realistic attacks  (lower is better)

A generator is on the frontier if no other generator is at least as good on all three axes and
strictly better on one. Frontier membership is also bootstrapped over seeds, so a generator that is
only ahead by seed noise shows up as a low frequency instead of a clean win.

    python pareto.py
"""

import json
from collections import defaultdict
from pathlib import Path

import numpy as np

RESULTS_DIR = Path("results")
N_BOOT = 2000
AXES = ("fidelity_js", "utility_tstr", "privacy_worst_mia")
SIGN = np.array([1.0, -1.0, 1.0])  # multiply so that lower is better on every axis


def per_seed_points(result):
    m = result["metrics"]
    return [
        m["fidelity"]["mean_js_divergence"],
        float(np.mean(list(m["utility"]["tstr_auroc"].values()))),
        m["privacy"]["membership_worst_case"]["mean_attack_auroc"],
    ]


def load(results_dir=RESULTS_DIR):
    by_generator = defaultdict(list)
    for path in sorted(results_dir.glob("*.json")):
        result = json.loads(path.read_text())
        by_generator[result["generator_name"]].append(per_seed_points(result))
    return {g: np.array(rows) for g, rows in by_generator.items()}


def dominates(a, b):
    a, b = a * SIGN, b * SIGN
    return bool(np.all(a <= b) and np.any(a < b))


def frontier(points):
    names = list(points)
    return [n for n in names if not any(dominates(points[m], points[n]) for m in names if m != n)]


def bootstrap(seed_points, rng):
    names = list(seed_points)
    on_frontier = dict.fromkeys(names, 0)
    dominated_by = {(a, b): 0 for a in names for b in names if a != b}
    for _ in range(N_BOOT):
        means = {
            n: seed_points[n][rng.integers(0, len(seed_points[n]), len(seed_points[n]))].mean(axis=0)
            for n in names
        }
        for n in frontier(means):
            on_frontier[n] += 1
        for (a, b) in dominated_by:
            dominated_by[(a, b)] += dominates(means[a], means[b])
    return {n: c / N_BOOT for n, c in on_frontier.items()}, {k: c / N_BOOT for k, c in dominated_by.items()}


def main():
    seed_points = load()
    if not seed_points:
        raise SystemExit("no results/*.json found; run eval_runner.py first")

    means = {g: rows.mean(axis=0) for g, rows in seed_points.items()}
    front = set(frontier(means))
    freq, dom = bootstrap(seed_points, np.random.default_rng(0))

    print(f"{'generator':24s} {'seeds':>5s} {'fidelity JS':>17s} {'utility TSTR':>17s} {'privacy worst MIA':>19s} {'frontier':>9s} {'boot freq':>10s}")
    for g, rows in seed_points.items():
        cells = [f"{rows[:, i].mean():.4f} +/- {rows[:, i].std(ddof=1):.4f}" for i in range(3)]
        print(f"{g:24s} {len(rows):5d} {cells[0]:>17s} {cells[1]:>17s} {cells[2]:>19s} {'yes' if g in front else 'no':>9s} {freq[g]:10.2f}")

    print("\nP(row generator dominates column generator), bootstrap over seeds")
    names = list(seed_points)
    print(f"{'':24s}" + "".join(f"{n:>24s}" for n in names))
    for a in names:
        print(f"{a:24s}" + "".join(f"{('-' if a == b else f'{dom[(a, b)]:.2f}'):>24s}" for b in names))


if __name__ == "__main__":
    main()
