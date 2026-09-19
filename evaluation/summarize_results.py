"""
Doppel - Track 2: mean and std of every headline metric per generator, over all seeds in results/.

    python -m evaluation.summarize_results
"""

import json
from collections import defaultdict
from pathlib import Path

import numpy as np

CLASSIFIERS = ("logistic_regression", "random_forest")


def headline(result):
    m = result["metrics"]
    row = {
        "mean_js": m["fidelity"]["mean_js_divergence"],
        "corr_diff": m["fidelity"]["correlation_diff"],
        "ks_pass": m["fidelity"]["ks_pass_fraction"],
        "mia_auroc": m["privacy"]["membership_inference"]["mean_attack_auroc"],
        "mia_gower_auroc": m["privacy"]["membership_inference_gower"]["mean_attack_auroc"],
        "mia_codes_auroc": m["privacy"]["membership_inference_codes"]["mean_attack_auroc"],
        "mia_worst_case": m["privacy"]["membership_worst_case"]["mean_attack_auroc"],
        "attr_uplift": m["privacy"]["attribute_inference"]["uplift"],
    }
    for t, r in m["privacy"]["attribute_inference_targets"].items():
        row[f"attr_{t}_uplift_members"] = r["uplift_members"]
        row[f"attr_{t}_gap"] = r["member_gap"]
    for c in CLASSIFIERS:
        row[f"tstr_{c}"] = m["utility"]["tstr_auroc"][c]
        row[f"gap_{c}"] = m["utility"]["gap"][c]
    return row


def main():
    runs = defaultdict(list)
    for path in sorted(Path("results").glob("*.json")):
        result = json.loads(path.read_text())
        runs[result["generator_name"]].append(headline(result))

    for name, rows in runs.items():
        print(f"{name}  (n_seeds={len(rows)})")
        for key in rows[0]:
            vals = np.array([r[key] for r in rows])
            print(f"  {key:28s} {vals.mean():.4f} +/- {vals.std(ddof=1) if len(vals) > 1 else 0:.4f}")


if __name__ == "__main__":
    main()
