"""
Doppel — Track 2 (Privacy & Utility Evaluation) fidelity metrics.
"""

import pandas as pd
import numpy as np
from scipy.spatial.distance import jensenshannon
from scipy.stats import ks_2samp

ID_COLS = ["subject_id", "hadm_id", "icd9_codes", "split"]

CATEGORICAL_COLS = [
    "admission_type", "ethnicity", "first_careunit", "gender", "icd9_primary",
]

CONTINUOUS_COLS = ["age", "los_hospital_days", "los_icu_days", "n_diagnoses"]

BINARY_COLS = ["hospital_expire_flag", "readmit_30d", "age_89_plus"]

NUMERIC_COLS = CONTINUOUS_COLS + ["hospital_expire_flag", "readmit_30d"]


def infer_lab_cols(df):
    return [c for c in df.columns if c.startswith("lab_")]


def js_divergence_categorical(real, synth):
    real = real.dropna().astype(str)
    synth = synth.dropna().astype(str)
    categories = sorted(set(real.unique()) | set(synth.unique()))
    real_p = real.value_counts(normalize=True).reindex(categories, fill_value=0.0)
    synth_p = synth.value_counts(normalize=True).reindex(categories, fill_value=0.0)
    return jensenshannon(real_p.values, synth_p.values, base=2) ** 2


def js_divergence_continuous(real, synth, bins=10):
    real = real.dropna()
    synth = synth.dropna()
    combined = pd.concat([real, synth])
    edges = np.quantile(combined, np.linspace(0, 1, bins + 1))
    edges = np.unique(edges)
    if len(edges) < 2:
        return 0.0
    real_counts, _ = np.histogram(real, bins=edges)
    synth_counts, _ = np.histogram(synth, bins=edges)
    real_p = real_counts / max(real_counts.sum(), 1)
    synth_p = synth_counts / max(synth_counts.sum(), 1)
    return jensenshannon(real_p, synth_p, base=2) ** 2


def dimension_wise_js(real_df, synth_df, categorical_cols, numeric_cols):
    results = {}
    for col in categorical_cols:
        if col in real_df.columns and col in synth_df.columns:
            results[col] = js_divergence_categorical(real_df[col], synth_df[col])
    for col in numeric_cols:
        if col in real_df.columns and col in synth_df.columns:
            results[col] = js_divergence_continuous(real_df[col], synth_df[col])
    return results


def correlation_preservation(real_df, synth_df, numeric_cols):
    cols = [c for c in numeric_cols if c in real_df.columns and c in synth_df.columns]
    real_corr = real_df[cols].corr().values
    synth_corr = synth_df[cols].corr().values
    mask = np.triu(np.ones_like(real_corr, dtype=bool), k=1)
    real_upper = np.nan_to_num(real_corr[mask])
    synth_upper = np.nan_to_num(synth_corr[mask])
    return float(np.mean(np.abs(real_upper - synth_upper)))


def dimension_wise_ks(real_df, synth_df, numeric_cols):
    results = {}
    for col in numeric_cols:
        if col in real_df.columns and col in synth_df.columns:
            real_vals = real_df[col].dropna()
            synth_vals = synth_df[col].dropna()
            if len(real_vals) < 2 or len(synth_vals) < 2:
                continue
            stat, p = ks_2samp(real_vals, synth_vals)
            results[col] = {"statistic": float(stat), "p_value": float(p)}
    return results


def run_fidelity_report(real_df, synth_df):
    lab_cols = infer_lab_cols(real_df)
    numeric_cols = NUMERIC_COLS + lab_cols

    js_scores = dimension_wise_js(
        real_df, synth_df, CATEGORICAL_COLS + BINARY_COLS, CONTINUOUS_COLS + lab_cols
    )
    mean_js = float(np.mean(list(js_scores.values()))) if js_scores else float("nan")

    corr_diff = correlation_preservation(real_df, synth_df, numeric_cols)

    ks_results = dimension_wise_ks(real_df, synth_df, numeric_cols)
    ks_pass_frac = (
        np.mean([r["p_value"] >= 0.05 for r in ks_results.values()])
        if ks_results else float("nan")
    )

    return {
        "mean_js_divergence": mean_js,
        "per_column_js": js_scores,
        "correlation_diff": corr_diff,
        "ks_pass_fraction": ks_pass_frac,
        "per_column_ks": ks_results,
    }


def main():
    df = pd.read_csv("output/mimic_demo_clean.csv")
    real = df[df["split"] == "holdout"]
    synth_stand_in = df[df["split"] == "train"]

    report = run_fidelity_report(real, synth_stand_in)

    print(f"Mean JS divergence: {report['mean_js_divergence']:.4f}")
    print(f"Correlation preservation (mean abs diff): {report['correlation_diff']:.4f}")
    print(f"KS test pass fraction (p >= 0.05): {report['ks_pass_fraction']:.4f}")
    print()
    print("Per-column JS divergence:")
    for col, score in sorted(report["per_column_js"].items(), key=lambda x: -x[1]):
        print(f"  {col}: {score:.4f}")


if __name__ == "__main__":
    main()
