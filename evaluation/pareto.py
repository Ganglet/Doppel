"""
Doppel - Track 2: fidelity / utility / privacy Pareto frontier over generator arms.

Reads every results/<arm>_seed<n>.json and reduces each arm to metrics per seed. The main frontier uses

  fidelity   mean JS divergence vs real train                                (lower is better)
  utility    mean of the two TSTR AUROCs (LR and random forest)              (higher is better)
  privacy    worst-case membership AUROC over the realistic attacks          (lower is better)

An arm is on the frontier if no other arm is at least as good on every axis and strictly better on one.
Frontier membership is bootstrapped over seeds. The frontier is then recomputed under other reasonable
axis choices, because a frontier that changes with the axes is a statement about the axes.

    python -m evaluation.pareto
"""

import json
from collections import defaultdict
from pathlib import Path

import numpy as np

RESULTS_DIR = Path("results")
N_BOOT = 2000

METRICS = ["fidelity_js", "corr_diff", "tstr_lr", "tstr_rf", "utility_tstr",
           "mia_numeric", "mia_gower", "mia_codes", "mia_worst"]
HIGHER_IS_BETTER = {"tstr_lr", "tstr_rf", "utility_tstr"}

AXIS_SETS = {
    "main": ["fidelity_js", "utility_tstr", "mia_worst"],
    "+ correlation axis": ["fidelity_js", "corr_diff", "utility_tstr", "mia_worst"],
    "utility = LR only": ["fidelity_js", "tstr_lr", "mia_worst"],
    "utility = RF only": ["fidelity_js", "tstr_rf", "mia_worst"],
    "privacy = 4 numeric": ["fidelity_js", "utility_tstr", "mia_numeric"],
    "privacy = Gower": ["fidelity_js", "utility_tstr", "mia_gower"],
    "privacy = ICD-9 codes": ["fidelity_js", "utility_tstr", "mia_codes"],
    "no utility axis": ["fidelity_js", "mia_worst"],
}


def per_seed_metrics(result):
    m = result["metrics"]
    tstr = m["utility"]["tstr_auroc"]
    p = m["privacy"]
    return [
        m["fidelity"]["mean_js_divergence"],
        m["fidelity"]["correlation_diff"],
        tstr["logistic_regression"],
        tstr["random_forest"],
        float(np.mean(list(tstr.values()))),
        p["membership_inference"]["mean_attack_auroc"],
        p["membership_inference_gower"]["mean_attack_auroc"],
        p["membership_inference_codes"]["mean_attack_auroc"],
        p["membership_worst_case"]["mean_attack_auroc"],
    ]


def load(results_dir=RESULTS_DIR):
    by_arm = defaultdict(list)
    for path in sorted(results_dir.glob("*.json")):
        result = json.loads(path.read_text())
        by_arm[result["generator_name"]].append(per_seed_metrics(result))
    return {arm: np.array(rows) for arm, rows in by_arm.items()}


def oriented(vector, axes):
    """Pick the axes and flip signs so that lower is better on every one."""
    idx = [METRICS.index(a) for a in axes]
    sign = np.array([-1.0 if a in HIGHER_IS_BETTER else 1.0 for a in axes])
    return np.asarray(vector)[idx] * sign


def dominates(a, b):
    return bool(np.all(a <= b) and np.any(a < b))


def frontier(points):
    names = list(points)
    return [n for n in names if not any(dominates(points[m], points[n]) for m in names if m != n)]


def bootstrap(seed_points, axes, rng, n_boot=N_BOOT):
    names = list(seed_points)
    on_frontier = dict.fromkeys(names, 0)
    dominated_by = {(a, b): 0 for a in names for b in names if a != b}
    for _ in range(n_boot):
        means = {
            n: oriented(seed_points[n][rng.integers(0, len(seed_points[n]), len(seed_points[n]))].mean(axis=0), axes)
            for n in names
        }
        for n in frontier(means):
            on_frontier[n] += 1
        for (a, b) in dominated_by:
            dominated_by[(a, b)] += dominates(means[a], means[b])
    return {n: c / n_boot for n, c in on_frontier.items()}, {k: c / n_boot for k, c in dominated_by.items()}


def main():
    seed_points = load()
    if not seed_points:
        raise SystemExit("no results/*.json found; run evaluation.eval_runner first")
    names = list(seed_points)
    rng = np.random.default_rng(0)

    main_axes = AXIS_SETS["main"]
    means = {a: oriented(rows.mean(axis=0), main_axes) for a, rows in seed_points.items()}
    front = set(frontier(means))
    freq, dom = bootstrap(seed_points, main_axes, rng)

    print(f"{'arm':28s} {'seeds':>5s} {'fidelity JS':>17s} {'utility TSTR':>17s} {'privacy worst MIA':>19s} {'frontier':>9s} {'boot freq':>10s}")
    for a, rows in seed_points.items():
        cells = [f"{rows[:, METRICS.index(k)].mean():.4f} +/- {rows[:, METRICS.index(k)].std(ddof=1):.4f}" for k in ("fidelity_js", "utility_tstr", "mia_worst")]
        print(f"{a:28s} {len(rows):5d} {cells[0]:>17s} {cells[1]:>17s} {cells[2]:>19s} {'yes' if a in front else 'no':>9s} {freq[a]:10.2f}")

    print("\nP(row arm dominates column arm) on the main axes, bootstrap over seeds")
    print(f"{'':28s}" + "".join(f"{n[:17]:>18s}" for n in names))
    for a in names:
        print(f"{a:28s}" + "".join(f"{('-' if a == b else f'{dom[(a, b)]:.2f}'):>18s}" for b in names))

    print("\nSensitivity: bootstrap frequency of being on the frontier under other axis choices")
    header = list(AXIS_SETS)
    print(f"{'arm':28s}" + "".join(f"{h[:19]:>21s}" for h in header))
    table = {a: [] for a in names}
    for axes in AXIS_SETS.values():
        f, _ = bootstrap(seed_points, axes, rng, n_boot=1000)
        for a in names:
            table[a].append(f[a])
    for a in names:
        print(f"{a:28s}" + "".join(f"{v:21.2f}" for v in table[a]))

    print("\nPrivacy ordering on each attack (mean AUROC, higher = more leakage)")
    for k in ("mia_numeric", "mia_gower", "mia_codes", "mia_worst"):
        order = sorted(names, key=lambda a: -seed_points[a][:, METRICS.index(k)].mean())
        print(f"  {k:12s} " + " > ".join(f"{a} ({seed_points[a][:, METRICS.index(k)].mean():.3f})" for a in order))


if __name__ == "__main__":
    main()
