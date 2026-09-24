"""
Doppel - Track 2 (Privacy & Utility Evaluation) membership-inference attack.

Shadow-model attack: train several shadow "generators" on random member subsets of the
population, measure each population record's nearest-neighbor distance to the resulting
synthetic data, and train an attack classifier to predict membership from that distance.

`generator_fn` is pluggable - swap in a real Track 1 generator once available. The naive
stand-in generator here (resample + Gaussian noise) exists only to exercise this harness
end-to-end before real synthetic data exists.
"""

import json

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, roc_curve
from sklearn.preprocessing import MultiLabelBinarizer, StandardScaler

NUMERIC_COLS = ["age", "los_hospital_days", "los_icu_days", "n_diagnoses"]

GOWER_CATEGORICAL = ["admission_type", "ethnicity", "first_careunit", "gender", "icd9_primary",
                     "hospital_expire_flag", "readmit_30d", "age_89_plus"]


def naive_stand_in_generator(train_df, numeric_cols, n_samples, noise_scale=0.3, seed=None):
    rng = np.random.default_rng(seed)
    sample = train_df[numeric_cols].sample(n=n_samples, replace=True, random_state=seed).reset_index(drop=True)
    stds = train_df[numeric_cols].std().values
    noise = rng.normal(loc=0.0, scale=noise_scale, size=sample.shape) * stds
    return sample + noise


def nearest_neighbor_distances(records, synth_matrix):
    dists = np.zeros(len(records))
    for i, record in enumerate(records):
        diffs = synth_matrix - record
        dists[i] = np.sqrt((diffs ** 2).sum(axis=1)).min()
    return dists


def codes_distances(pop_df, synth_df, keep_codes=None):
    pop_codes = [json.loads(v) for v in pop_df["icd9_codes"]]
    synth_codes = [json.loads(v) for v in synth_df["icd9_codes"]]
    if keep_codes is not None:
        pop_codes = [[c for c in row if c in keep_codes] for row in pop_codes]
        synth_codes = [[c for c in row if c in keep_codes] for row in synth_codes]
    mlb = MultiLabelBinarizer(sparse_output=False)
    mlb.fit(pop_codes + synth_codes)
    a = mlb.transform(pop_codes).astype(float)
    b = mlb.transform(synth_codes).astype(float)
    inter = a @ b.T
    union = a.sum(axis=1)[:, None] + b.sum(axis=1)[None, :] - inter
    return 1.0 - np.divide(inter, union, out=np.ones_like(inter), where=union > 0)


def gower_distances(pop_df, synth_df):
    # numeric columns are scaled by the range of pop_df, so score members and non-members in one call
    lab_cols = [c for c in pop_df.columns if c.startswith("lab_")]
    num_cols = NUMERIC_COLS + lab_cols
    pop_num = pop_df[num_cols].to_numpy(float)
    syn_num = synth_df[num_cols].to_numpy(float)
    span = np.nanmax(pop_num, axis=0) - np.nanmin(pop_num, axis=0)
    span = np.where(np.isfinite(span) & (span > 0), span, 1.0)

    d_num = np.abs(pop_num[:, None, :] - syn_num[None, :, :]) / span
    both_nan = np.isnan(pop_num)[:, None, :] & np.isnan(syn_num)[None, :, :]
    d_num = np.where(np.isnan(d_num), np.where(both_nan, 0.0, 1.0), np.minimum(d_num, 1.0))
    total = d_num.sum(axis=2)

    for c in GOWER_CATEGORICAL:
        total += (pop_df[c].astype(str).to_numpy()[:, None] != synth_df[c].astype(str).to_numpy()[None, :])

    total += codes_distances(pop_df, synth_df)

    return total / (len(num_cols) + len(GOWER_CATEGORICAL) + 1)


def build_shadow_attack_dataset(
    population_df, generator_fn, numeric_cols, n_shadow=10, member_frac=0.5, seed=42, distance_fn=None
):
    rng = np.random.default_rng(seed)
    scaler = StandardScaler()
    scaler.fit(population_df[numeric_cols])
    pop_scaled = scaler.transform(population_df[numeric_cols])
    n_pop = len(population_df)

    rows = []
    for shadow_id in range(n_shadow):
        member_idx = set(
            rng.choice(n_pop, size=int(n_pop * member_frac), replace=False).tolist()
        )
        member_df = population_df.iloc[list(member_idx)]

        synth_df = generator_fn(member_df, numeric_cols, n_samples=len(member_df), seed=seed + shadow_id)

        if distance_fn is None:
            synth_scaled = scaler.transform(synth_df[numeric_cols])
            dists = nearest_neighbor_distances(pop_scaled, synth_scaled)
            knn3 = None
        else:
            full = np.sort(distance_fn(population_df, synth_df), axis=1)
            dists, knn3 = full[:, 0], full[:, :3].mean(axis=1)

        for i in range(n_pop):
            row = {"shadow_id": shadow_id, "record": i, "min_dist": dists[i], "is_member": int(i in member_idx)}
            if knn3 is not None:
                row["knn3_dist"] = knn3[i]
            rows.append(row)

    return pd.DataFrame(rows)


FPR_LEVELS = {"tpr_at_fpr_5pct": 0.05, "tpr_at_fpr_1pct": 0.01}


def record_advantage(attack_df, n_pop):
    """Per record: mean min-distance when it was a non-member minus when it was a member. Positive means the
    generator sits closer to the record when it was trained on it. NaN if a record was never on one side."""
    members = attack_df[attack_df["is_member"] == 1].groupby("record")["min_dist"].mean()
    others = attack_df[attack_df["is_member"] == 0].groupby("record")["min_dist"].mean()
    return (others - members).reindex(range(n_pop)).to_numpy()


def evaluate_attack(attack_df):
    aucs, pooled_labels, pooled_scores = [], [], []
    features = [c for c in attack_df.columns if c not in ("shadow_id", "record", "is_member")]
    for held_out_shadow in attack_df["shadow_id"].unique():
        train_rows = attack_df[attack_df["shadow_id"] != held_out_shadow]
        test_rows = attack_df[attack_df["shadow_id"] == held_out_shadow]

        model = LogisticRegression()
        model.fit(train_rows[features], train_rows["is_member"])
        preds = model.predict_proba(test_rows[features])[:, 1]
        aucs.append(roc_auc_score(test_rows["is_member"], preds))
        pooled_labels.append(test_rows["is_member"].to_numpy())
        pooled_scores.append(preds)

    fpr, tpr, _ = roc_curve(np.concatenate(pooled_labels), np.concatenate(pooled_scores))
    tprs = {name: float(tpr[fpr <= level].max()) for name, level in FPR_LEVELS.items()}
    return {"mean_attack_auroc": float(np.mean(aucs)), "per_shadow_auroc": aucs, **tprs}


def run_membership_inference(
    population_df, generator_fn, numeric_cols, n_shadow=10, seed=42, distance_fn=None, return_records=False
):
    attack_df = build_shadow_attack_dataset(
        population_df, generator_fn, numeric_cols, n_shadow=n_shadow, seed=seed, distance_fn=distance_fn
    )
    result = evaluate_attack(attack_df)
    if return_records:
        result["record_advantage"] = record_advantage(attack_df, len(population_df)).tolist()
    return result


def main():
    df = pd.read_csv("output/mimic_demo_clean.csv")
    population = df[df["split"] == "train"].reset_index(drop=True)

    print("Sanity check - memorizing generator (noise_scale=0.0), expect attack AUROC near 1.0:")
    memorizing_fn = lambda d, cols, n_samples, seed: naive_stand_in_generator(
        d, cols, n_samples, noise_scale=0.0, seed=seed
    )
    result = run_membership_inference(population, memorizing_fn, NUMERIC_COLS, n_shadow=8)
    print(f"  mean attack AUROC: {result['mean_attack_auroc']:.4f}")
    print()

    print("Noisy generator (noise_scale=0.3), expect attack AUROC closer to 0.5:")
    noisy_fn = lambda d, cols, n_samples, seed: naive_stand_in_generator(
        d, cols, n_samples, noise_scale=0.3, seed=seed
    )
    result = run_membership_inference(population, noisy_fn, NUMERIC_COLS, n_shadow=8)
    print(f"  mean attack AUROC: {result['mean_attack_auroc']:.4f}")


if __name__ == "__main__":
    main()
