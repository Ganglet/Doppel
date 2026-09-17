"""
Doppel — Track 2 (Privacy & Utility Evaluation) downstream utility pipeline.
"""

import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import roc_auc_score
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import OneHotEncoder, StandardScaler

TARGET_COL = "hospital_expire_flag"

DROP_COLS = ["subject_id", "hadm_id", "icd9_codes", "icd9_primary", "split", "readmit_30d"]

CATEGORICAL_COLS = ["admission_type", "ethnicity", "first_careunit", "gender"]

CLASSIFIERS = {
    "logistic_regression": lambda: LogisticRegression(max_iter=1000),
    "random_forest": lambda: RandomForestClassifier(n_estimators=200, random_state=42),
}


def build_features(df, encoder=None, num_imputer=None, num_scaler=None, fit=False):
    df = df.drop(columns=[c for c in DROP_COLS if c in df.columns])
    y = df[TARGET_COL].values
    X_cat = df[CATEGORICAL_COLS].fillna("MISSING")
    X_num = df.drop(columns=CATEGORICAL_COLS + [TARGET_COL])

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


def trtr_baseline(train_df, n_splits=5, seed=42):
    df = train_df.reset_index(drop=True)
    y = df[TARGET_COL].values
    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=seed)

    scores = {name: [] for name in CLASSIFIERS}
    for train_idx, test_idx in skf.split(df, y):
        fold_train = df.iloc[train_idx]
        fold_test = df.iloc[test_idx]

        X_train, y_train, encoder, imputer, scaler = build_features(fold_train, fit=True)
        X_test, y_test, _, _, _ = build_features(
            fold_test, encoder=encoder, num_imputer=imputer, num_scaler=scaler, fit=False
        )

        for name, make_model in CLASSIFIERS.items():
            model = make_model()
            model.fit(X_train, y_train)
            preds = model.predict_proba(X_test)[:, 1]
            scores[name].append(roc_auc_score(y_test, preds))

    return {name: float(np.mean(vals)) for name, vals in scores.items()}


def tstr_eval(synthetic_train_df, real_holdout_df):
    X_train, y_train, encoder, imputer, scaler = build_features(synthetic_train_df, fit=True)
    X_test, y_test, _, _, _ = build_features(
        real_holdout_df, encoder=encoder, num_imputer=imputer, num_scaler=scaler, fit=False
    )

    scores = {}
    for name, make_model in CLASSIFIERS.items():
        model = make_model()
        model.fit(X_train, y_train)
        preds = model.predict_proba(X_test)[:, 1]
        scores[name] = float(roc_auc_score(y_test, preds))
    return scores


def utility_gap_report(train_df, holdout_df, synthetic_df):
    trtr = trtr_baseline(train_df)
    tstr = tstr_eval(synthetic_df, holdout_df)
    gap = {name: trtr[name] - tstr[name] for name in CLASSIFIERS}
    return {"trtr_auroc": trtr, "tstr_auroc": tstr, "gap": gap}


def main():
    df = pd.read_csv("output/mimic_demo_clean.csv")
    train_df = df[df["split"] == "train"]
    holdout_df = df[df["split"] == "holdout"]

    report = utility_gap_report(train_df, holdout_df, synthetic_df=train_df)

    print("TRTR baseline (5-fold CV on real train):")
    for name, auc in report["trtr_auroc"].items():
        print(f"  {name}: {auc:.4f}")
    print()
    print("TSTR (train on stand-in synthetic, test on real holdout):")
    for name, auc in report["tstr_auroc"].items():
        print(f"  {name}: {auc:.4f}")
    print()
    print("Gap (TRTR - TSTR):")
    for name, gap in report["gap"].items():
        print(f"  {name}: {gap:.4f}")


if __name__ == "__main__":
    main()
