"""
Doppel - Track 2 (Privacy & Utility Evaluation) attribute-inference attack.

Attacker sees a real record with the sensitive attribute withheld, and a classifier
trained on synthetic data to predict that attribute from the rest. Success is measured
as accuracy uplift over the population base rate (always guessing the majority class).
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
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


def main():
    df = pd.read_csv("output/mimic_demo_clean.csv")
    train_df = df[df["split"] == "train"]
    holdout_df = df[df["split"] == "holdout"]

    result = run_attribute_inference(synthetic_train_df=train_df, real_holdout_df=holdout_df)

    print(f"Target attribute: {TARGET_COL}")
    print(f"Attacker accuracy: {result['attacker_accuracy']:.4f}")
    print(f"Base rate accuracy (majority class): {result['base_rate_accuracy']:.4f}")
    print(f"Uplift (attacker - base rate): {result['uplift']:.4f}")


if __name__ == "__main__":
    main()
