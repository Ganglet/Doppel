"""
Doppel - Track 2 (Privacy & Utility Evaluation) membership-inference attack.

Shadow-model attack: train several shadow "generators" on random member subsets of the
population, measure each population record's nearest-neighbor distance to the resulting
synthetic data, and train an attack classifier to predict membership from that distance.

`generator_fn` is pluggable - swap in a real Track 1 generator once available. The naive
stand-in generator here (resample + Gaussian noise) exists only to exercise this harness
end-to-end before real synthetic data exists.
"""

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.preprocessing import StandardScaler

NUMERIC_COLS = ["age", "los_hospital_days", "los_icu_days", "n_diagnoses"]


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


def build_shadow_attack_dataset(
    population_df, generator_fn, numeric_cols, n_shadow=10, member_frac=0.5, seed=42
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
        synth_scaled = scaler.transform(synth_df[numeric_cols])

        dists = nearest_neighbor_distances(pop_scaled, synth_scaled)
        for i in range(n_pop):
            rows.append({
                "shadow_id": shadow_id,
                "min_dist": dists[i],
                "is_member": int(i in member_idx),
            })

    return pd.DataFrame(rows)


def evaluate_attack(attack_df):
    aucs = []
    for held_out_shadow in attack_df["shadow_id"].unique():
        train_rows = attack_df[attack_df["shadow_id"] != held_out_shadow]
        test_rows = attack_df[attack_df["shadow_id"] == held_out_shadow]

        model = LogisticRegression()
        model.fit(train_rows[["min_dist"]], train_rows["is_member"])
        preds = model.predict_proba(test_rows[["min_dist"]])[:, 1]
        aucs.append(roc_auc_score(test_rows["is_member"], preds))

    return {"mean_attack_auroc": float(np.mean(aucs)), "per_shadow_auroc": aucs}


def run_membership_inference(population_df, generator_fn, numeric_cols, n_shadow=10, seed=42):
    attack_df = build_shadow_attack_dataset(
        population_df, generator_fn, numeric_cols, n_shadow=n_shadow, seed=seed
    )
    return evaluate_attack(attack_df)


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
