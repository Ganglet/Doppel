"""
Doppel - Track 2 (Privacy & Utility Evaluation) attribute-inference attack.

Attacker sees a real record with the sensitive attribute withheld, and a classifier
trained on synthetic data to predict that attribute from the rest. Success is measured
as accuracy uplift over the population base rate (always guessing the majority class).
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, balanced_accuracy_score
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import OneHotEncoder, StandardScaler

TARGET_COL = "ethnicity"

DROP_COLS = ["subject_id", "hadm_id", "icd9_codes", "split"]

CATEGORICAL_PREDICTORS = ["admission_type", "first_careunit", "gender", "icd9_primary"]


def build_features(df, encoder=None, num_imputer=None, num_scaler=None, fit=False):
    df = df.drop(columns=[c for c in DROP_COLS if c in df.columns])
    y = df[TARGET_COL].astype(str).values
    X_cat = df[CATEGORICAL_PREDICTORS].fillna("MISSING")
    X_num = df.drop(columns=CATEGORICAL_PREDICTORS + [TARGET_COL])

    if fit:
        encoder = OneHotEncoder(handle_unknown="ignore", sparse_output=False)
        encoder.fit(X_cat)
        num_imputer = SimpleImputer(strategy="median")
        num_imputer.fit(X_num)
        num_scaler = StandardScaler()
        num_scaler.fit(num_imputer.transform(X_num))

    X_cat_enc = encoder.transform(X_cat)
    X_num_imp = num_scaler.transform(num_imputer.transform(X_num))

    X = np.hstack([X_num_imp, X_cat_enc])
    return X, y, encoder, num_imputer, num_scaler


def base_rate_accuracy(y_true):
    values, counts = np.unique(y_true, return_counts=True)
    return counts.max() / counts.sum()


def run_attribute_inference(synthetic_train_df, real_holdout_df):
    X_train, y_train, encoder, imputer, scaler = build_features(synthetic_train_df, fit=True)
    X_test, y_test, _, _, _ = build_features(
        real_holdout_df, encoder=encoder, num_imputer=imputer, num_scaler=scaler, fit=False
    )

    model = RandomForestClassifier(n_estimators=200, random_state=42)
    model.fit(X_train, y_train)
    preds = model.predict(X_test)

    attacker_acc = accuracy_score(y_test, preds)
    base_rate = base_rate_accuracy(y_test)

    return {
        "attacker_accuracy": float(attacker_acc),
        "base_rate_accuracy": float(base_rate),
        "uplift": float(attacker_acc - base_rate),
    }


AGE_BUCKET_EDGES = [0, 64, 79, 200]
AGE_BUCKET_LABELS = ["<65", "65-79", "80+"]

ATTRIBUTE_TARGETS = {
    "gender": {"exclude": []},
    "first_careunit": {"exclude": []},
    "age_bucket": {"exclude": ["age", "age_89_plus"]},
}

CATEGORICAL_ALL = ["admission_type", "ethnicity", "first_careunit", "gender", "icd9_primary"]


def _with_age_bucket(df):
    df = df.copy()
    df["age_bucket"] = pd.cut(df["age"], AGE_BUCKET_EDGES, labels=AGE_BUCKET_LABELS).astype(str)
    return df


def _target_features(df, target, encoder=None, num_imputer=None, num_scaler=None, fit=False):
    df = _with_age_bucket(df)
    y = df[target].astype(str).values
    drop = [c for c in DROP_COLS if c in df.columns] + ["age_bucket"] + ATTRIBUTE_TARGETS[target]["exclude"]
    cat_cols = [c for c in CATEGORICAL_ALL if c != target]
    X_cat = df[cat_cols].astype(str).fillna("MISSING")
    X_num = df.drop(columns=[c for c in drop if c in df.columns] + cat_cols)
    X_num = X_num.drop(columns=[target], errors="ignore")

    if fit:
        encoder = OneHotEncoder(handle_unknown="ignore", sparse_output=False).fit(X_cat)
        num_imputer = SimpleImputer(strategy="median").fit(X_num)
        num_scaler = StandardScaler().fit(num_imputer.transform(X_num))

    X = np.hstack([num_scaler.transform(num_imputer.transform(X_num)), encoder.transform(X_cat)])
    return X, y, encoder, num_imputer, num_scaler


def _uplift(model, X, y):
    chance = 1.0 / len(np.unique(y))
    acc = float(balanced_accuracy_score(y, model.predict(X)))
    return acc, chance, acc - chance


def run_attribute_targets(synthetic_df, train_df, holdout_df):
    results = {}
    for target in ATTRIBUTE_TARGETS:
        X_syn, y_syn, enc, imp, sc = _target_features(synthetic_df, target, fit=True)
        model = RandomForestClassifier(n_estimators=200, random_state=42).fit(X_syn, y_syn)
        X_mem, y_mem, _, _, _ = _target_features(train_df, target, enc, imp, sc)
        X_non, y_non, _, _, _ = _target_features(holdout_df, target, enc, imp, sc)
        acc_m, chance_m, up_m = _uplift(model, X_mem, y_mem)
        acc_n, chance_n, up_n = _uplift(model, X_non, y_non)
        results[target] = {
            "balanced_acc_members": acc_m, "chance_members": chance_m, "uplift_members": up_m,
            "balanced_acc_nonmembers": acc_n, "chance_nonmembers": chance_n, "uplift_nonmembers": up_n,
            "member_gap": up_m - up_n,
        }
    return results


def main():
    df = pd.read_csv("output/mimic_demo_clean.csv")
    train_df = df[df["split"] == "train"]
    holdout_df = df[df["split"] == "holdout"]

    result = run_attribute_inference(synthetic_train_df=train_df, real_holdout_df=holdout_df)

    print(f"Target attribute: {TARGET_COL}")
    print(f"Attacker accuracy: {result['attacker_accuracy']:.4f}")
    print(f"Base rate accuracy (majority class): {result['base_rate_accuracy']:.4f}")
    print(f"Uplift (attacker - base rate): {result['uplift']:.4f}")


def print_targets(title, results):
    print(title)
    print(f"  {'target':16s} {'members':>9s} {'non-mem':>9s} {'uplift(m)':>10s} {'uplift(n)':>10s} {'gap':>8s}")
    for t, r in results.items():
        print(f"  {t:16s} {r['balanced_acc_members']:9.3f} {r['balanced_acc_nonmembers']:9.3f}"
              f" {r['uplift_members']:10.3f} {r['uplift_nonmembers']:10.3f} {r['member_gap']:8.3f}")


if __name__ == "__main__":
    main()
    print()
    df = pd.read_csv("output/mimic_demo_clean.csv")
    train_df, holdout_df = df[df["split"] == "train"], df[df["split"] == "holdout"]
    print_targets("Ceiling control: attacker trained on an exact copy of the members", run_attribute_targets(train_df, train_df, holdout_df))
