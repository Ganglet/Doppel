"""
Doppel - export the evaluation results as one JSON file for the web dashboard.

Reads results/<arm>_seed<n>.json and results/calibration/mia_calibration.json (written by
evaluation.eval_runner and evaluation.mia_calibration), reuses evaluation.pareto for the frontier, and
writes web/public/data/dashboard.json. Aggregates only: no patient rows.

    python web/scripts/export_data.py
"""

import glob
import json
import subprocess
import sys
import warnings
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr, ttest_ind

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from evaluation import pareto as P  # noqa: E402
from evaluation.arms import resolve  # noqa: E402
from evaluation.fidelity_metrics import run_fidelity_report  # noqa: E402
from evaluation.membership_inference import gower_distances  # noqa: E402
from generators import schema as S  # noqa: E402

OUT = ROOT / "web" / "public" / "data" / "dashboard.json"
DOCS_REF = "track2-phase3-react-dashboard"

ARMS = [
    {"id": "independent_marginals", "label": "Independent marginals", "short": "Floor", "family": "floor",
     "family_label": "Reference floor", "marker": "square",
     "about": "Samples every column on its own, so it has no dependence between columns. It is the floor every real generator has to beat."},
    {"id": "gaussian_copula", "label": "Gaussian copula", "short": "Copula", "family": "copula",
     "family_label": "Statistical", "marker": "circle",
     "about": "A statistical baseline that keeps each column's distribution and adds correlation between columns (Ledoit-Wolf shrinkage)."},
    {"id": "gaussian_copula_shrink025", "label": "Gaussian copula, shrink 0.25", "short": "Copula 0.25", "family": "copula",
     "family_label": "Statistical", "marker": "diamond",
     "about": "The same copula with less shrinkage, so it keeps more of the real correlations. This is the config Track 1 carried into Phase 3."},
    {"id": "ctgan", "label": "CTGAN", "short": "CTGAN", "family": "ctgan",
     "family_label": "GAN", "marker": "triangle",
     "about": "A GAN for tables, trained for 300 epochs. At 94 training rows it learns almost nothing beyond the floor."},
    {"id": "tvae", "label": "TVAE", "short": "TVAE", "family": "tvae",
     "family_label": "VAE", "marker": "triangleDown",
     "about": "A variational autoencoder for tables, trained for 300 epochs. It memorizes training rows, which makes it the positive control for the privacy attacks."},
]
IDS = [a["id"] for a in ARMS]
ATTACKS = ["numeric4", "gower", "icd9_codes"]
TARGETS = ["gender", "first_careunit", "age_bucket"]


def ms(values):
    v = np.asarray(values, dtype=float)
    return {"mean": float(v.mean()), "sd": float(v.std(ddof=1)) if len(v) > 1 else 0.0}


def load_runs():
    runs = {}
    for arm in IDS:
        files = sorted(glob.glob(str(ROOT / "results" / f"{arm}_seed*.json")))
        if not files:
            raise SystemExit(f"no results for {arm}; run evaluation.eval_runner first")
        runs[arm] = [json.load(open(f, encoding="utf-8"))["metrics"] for f in files]
    return runs


def arm_summary(metrics):
    def col(fn):
        return [fn(m) for m in metrics]

    priv = lambda k, f="mean_attack_auroc": col(lambda m: m["privacy"][k][f])
    out = {
        "n_seeds": len(metrics),
        "fidelity": {
            "jsd": ms(col(lambda m: m["fidelity"]["mean_js_divergence"])),
            "corr_diff": ms(col(lambda m: m["fidelity"]["correlation_diff"])),
            "ks_pass": ms(col(lambda m: m["fidelity"]["ks_pass_fraction"])),
        },
        "utility": {
            "tstr_lr": ms(col(lambda m: m["utility"]["tstr_auroc"]["logistic_regression"])),
            "tstr_rf": ms(col(lambda m: m["utility"]["tstr_auroc"]["random_forest"])),
            "tstr_mean": ms(col(lambda m: np.mean(list(m["utility"]["tstr_auroc"].values())))),
        },
        "privacy": {
            "numeric4": ms(priv("membership_inference")),
            "gower": ms(priv("membership_inference_gower")),
            "codes": ms(priv("membership_inference_codes")),
            "worst": ms(col(lambda m: m["privacy"]["membership_worst_case"]["mean_attack_auroc"])),
            "tpr1_gower": ms(priv("membership_inference_gower", "tpr_at_fpr_1pct")),
            "tpr5_gower": ms(priv("membership_inference_gower", "tpr_at_fpr_5pct")),
            "tpr1_codes": ms(priv("membership_inference_codes", "tpr_at_fpr_1pct")),
            "tpr5_codes": ms(priv("membership_inference_codes", "tpr_at_fpr_5pct")),
        },
        "attribute_gap": {
            t: ms(col(lambda m, t=t: m["privacy"]["attribute_inference_targets"][t]["member_gap"])) for t in TARGETS
        },
        "per_seed": {
            "jsd": col(lambda m: m["fidelity"]["mean_js_divergence"]),
            "tstr_mean": col(lambda m: float(np.mean(list(m["utility"]["tstr_auroc"].values())))),
            "worst": col(lambda m: m["privacy"]["membership_worst_case"]["mean_attack_auroc"]),
        },
    }
    return out


def welch(a, b):
    return float(ttest_ind(a, b, equal_var=False)[1])


def tests(summaries):
    ps = lambda arm, key: np.array(summaries[arm]["per_seed"][key])
    out = {}
    for other in IDS:
        if other == "tvae":
            continue
        out[f"tvae_vs_{other}_worst_p"] = welch(ps("tvae", "worst"), ps(other, "worst"))
    out["tvae_vs_shrink025_utility_p"] = welch(ps("tvae", "tstr_mean"), ps("gaussian_copula_shrink025", "tstr_mean"))
    out["ctgan_vs_independent_worst_p"] = welch(ps("ctgan", "worst"), ps("independent_marginals", "worst"))
    out["ctgan_vs_independent_utility_p"] = welch(ps("ctgan", "tstr_mean"), ps("independent_marginals", "tstr_mean"))
    return out


def pareto_block():
    seed_points = P.load()
    rng = np.random.default_rng(0)
    main = P.AXIS_SETS["main"]
    means = {a: P.oriented(rows.mean(axis=0), main) for a, rows in seed_points.items()}
    front = set(P.frontier(means))
    freq, dom = P.bootstrap(seed_points, main, rng)
    sensitivity = {}
    for name, axes in P.AXIS_SETS.items():
        f, _ = P.bootstrap(seed_points, axes, rng, n_boot=1000)
        sensitivity[name] = {a: f[a] for a in IDS}
    order = {}
    for key in ("mia_numeric", "mia_gower", "mia_codes", "mia_worst"):
        i = P.METRICS.index(key)
        order[key] = sorted(IDS, key=lambda a: -float(seed_points[a][:, i].mean()))
    return {
        "axes": {"main": main},
        "frontier": {a: (a in front) for a in IDS},
        "frontier_freq": {a: freq[a] for a in IDS},
        "dominance": {a: {b: (None if a == b else dom[(a, b)]) for b in IDS} for a in IDS},
        "sensitivity": sensitivity,
        "privacy_order": order,
    }


def calibration_block():
    path = ROOT / "results" / "calibration" / "mia_calibration.json"
    d = json.load(open(path, encoding="utf-8"))
    arms = sorted(d["auroc"])
    attacks = list(next(iter(d["auroc"].values())))
    block = {
        "attacks": attacks,
        "auroc": {a: {k: ms(v) for k, v in d["auroc"][a].items()} for a in arms},
        "tpr1": {a: {k: ms(v) for k, v in d["tpr_at_fpr_1pct"][a].items()} for a in arms},
        "tpr5": {a: {k: ms(v) for k, v in d["tpr_at_fpr_5pct"][a].items()} for a in arms},
    }
    singles = np.array(d["singleton_codes_per_record"])
    rec = {}
    for a, adv in d["record_advantage_mean"].items():
        adv = np.array(adv, dtype=float)
        ok = ~np.isnan(adv)
        rho = float(spearmanr(adv[ok], singles[ok])[0]) if ok.sum() > 2 else None
        top = ok & (adv >= np.nanpercentile(adv, 90))
        rec[a] = {"spearman": rho, "top_decile": float(singles[top].mean()), "rest": float(singles[ok & ~top].mean())}
    block["per_record"] = rec
    return block


def coverage_block():
    real = S.load_real()
    train = real[real[S.SPLIT_COL] == S.TRAIN_SPLIT].reset_index(drop=True)
    out = {}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for arm in IDS:
            generator = resolve(arm)[0]
            distinct, most = [], []
            for seed in range(42, 62):
                path = S.SYNTH_DIR / "eval" / arm / f"{generator}_seed{seed}.csv"
                if not path.exists():
                    return {}
                nearest = gower_distances(train, S.load_real(path)).argmin(axis=0)
                counts = np.bincount(nearest, minlength=len(train))
                distinct.append(int((counts > 0).sum()))
                most.append(int(counts.max()))
            out[arm] = {"distinct": ms(distinct), "max_share": ms(most)}
    return out


def refs_block(summaries):
    real = S.load_real()
    train = real[real[S.SPLIT_COL] == S.TRAIN_SPLIT]
    holdout = real[real[S.SPLIT_COL] != S.TRAIN_SPLIT]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        floor = run_fidelity_report(holdout, train)
    first = json.load(open(sorted(glob.glob(str(ROOT / "results" / "tvae_seed*.json")))[0], encoding="utf-8"))
    trtr = first["metrics"]["utility"]["trtr_auroc"]
    return {
        "trtr_lr": trtr["logistic_regression"], "trtr_rf": trtr["random_forest"],
        "trtr_mean": float(np.mean(list(trtr.values()))),
        "real_vs_real_jsd": floor["mean_js_divergence"], "real_vs_real_corr": floor["correlation_diff"],
        "fail_line": 0.65, "good_band_top": 0.55,
    }


def dataset_block():
    real = S.load_real()
    train = real[real[S.SPLIT_COL] == S.TRAIN_SPLIT]
    holdout = real[real[S.SPLIT_COL] != S.TRAIN_SPLIT]
    return {
        "source": "MIMIC-III Clinical Database Demo v1.4", "patients": int(real["subject_id"].nunique()),
        "admissions": int(len(real)), "columns": int(real.shape[1]),
        "train": int(len(train)), "holdout": int(len(holdout)),
        "holdout_positives": int(holdout["hospital_expire_flag"].sum()),
        "mortality_rate": float(real["hospital_expire_flag"].mean()),
    }


def git(*args):
    try:
        return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    except Exception:
        return "unknown"


def main():
    runs = load_runs()
    summaries = {a: arm_summary(runs[a]) for a in IDS}
    data = {
        "meta": {
            "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "source_commit": git("rev-parse", "--short", "HEAD"),
            "runs": sum(s["n_seeds"] for s in summaries.values()),
            "seeds": [42, 61], "docs_ref": DOCS_REF, "repo": "https://github.com/Ganglet/Doppel",
        },
        "dataset": dataset_block(),
        "arms": ARMS,
        "refs": refs_block(summaries),
        "results": summaries,
        "tests": tests(summaries),
        "pareto": pareto_block(),
        "calibration": calibration_block(),
        "coverage": coverage_block(),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}  ({OUT.stat().st_size / 1024:.0f} KB, {data['meta']['runs']} runs)")


if __name__ == "__main__":
    main()
