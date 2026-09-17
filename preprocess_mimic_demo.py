"""
Doppel — Track 3 (Data Engineering) preprocessing pipeline.
"""

import json
import pandas as pd
import numpy as np
from pathlib import Path

RAW_DIR = Path(".")
OUT_DIR = Path("./output")
OUT_DIR.mkdir(exist_ok=True)

N_TOP_LABS = 20
TRAIN_FRAC = 0.8
RANDOM_SEED = 42


def load_raw():
    patients = pd.read_csv(RAW_DIR / "PATIENTS.csv")
    admissions = pd.read_csv(RAW_DIR / "ADMISSIONS.csv", parse_dates=["admittime", "dischtime"])
    icustays = pd.read_csv(RAW_DIR / "ICUSTAYS.csv")
    diagnoses = pd.read_csv(RAW_DIR / "DIAGNOSES_ICD.csv")
    d_icd_diagnoses = pd.read_csv(RAW_DIR / "D_ICD_DIAGNOSES.csv")
    labevents = pd.read_csv(RAW_DIR / "LABEVENTS.csv")
    d_labitems = pd.read_csv(RAW_DIR / "D_LABITEMS.csv")
    return patients, admissions, icustays, diagnoses, d_icd_diagnoses, labevents, d_labitems


def compute_age(patients, admissions):
    df = admissions[["subject_id", "hadm_id", "admittime"]].merge(
        patients[["subject_id", "dob"]], on="subject_id", how="left"
    )
    df["dob"] = pd.to_datetime(df["dob"], errors="coerce")
    earlier = (
        (df["admittime"].dt.month < df["dob"].dt.month) |
        ((df["admittime"].dt.month == df["dob"].dt.month) & (df["admittime"].dt.day < df["dob"].dt.day))
    )
    age_years = df["admittime"].dt.year - df["dob"].dt.year - earlier.astype(int)
    df["age"] = age_years.clip(upper=89).astype("Int64")
    df["age_89_plus"] = age_years > 89
    return df[["subject_id", "hadm_id", "age", "age_89_plus"]]


def build_admission_base(admissions, icustays):
    base = admissions.copy()
    base["los_hospital_days"] = (
        (base["dischtime"] - base["admittime"]).dt.total_seconds() / 86400
    )

    icu_agg = (
        icustays.groupby(["subject_id", "hadm_id"])
        .agg(los_icu_days=("los", "sum"), first_careunit=("first_careunit", "first"))
        .reset_index()
    )

    base = base.merge(icu_agg, on=["subject_id", "hadm_id"], how="left")

    keep_cols = [
        "subject_id", "hadm_id", "admittime", "admission_type", "ethnicity",
        "hospital_expire_flag", "los_hospital_days", "los_icu_days", "first_careunit",
    ]
    return base[keep_cols]


def collapse_ethnicity(series, top_n=6):
    top = series.value_counts().nlargest(top_n).index
    return series.where(series.isin(top), other="OTHER")


def build_diagnoses_features(diagnoses):
    diagnoses_sorted = diagnoses.sort_values(["subject_id", "hadm_id", "seq_num"])

    primary = (
        diagnoses_sorted[diagnoses_sorted["seq_num"] == 1]
        .rename(columns={"icd9_code": "icd9_primary"})[["subject_id", "hadm_id", "icd9_primary"]]
    )

    n_dx = (
        diagnoses.groupby(["subject_id", "hadm_id"]).size()
        .rename("n_diagnoses").reset_index()
    )

    code_lists = (
        diagnoses_sorted.groupby(["subject_id", "hadm_id"])["icd9_code"]
        .apply(lambda codes: json.dumps(list(codes)))
        .rename("icd9_codes").reset_index()
    )

    out = primary.merge(n_dx, on=["subject_id", "hadm_id"], how="outer")
    out = out.merge(code_lists, on=["subject_id", "hadm_id"], how="outer")
    return out


def build_lab_features(labevents, d_labitems, n_top=N_TOP_LABS):
    labs = labevents.dropna(subset=["hadm_id"]).copy()
    labs["hadm_id"] = labs["hadm_id"].astype(int)

    counts = labs.groupby("itemid")["hadm_id"].nunique().sort_values(ascending=False)
    top_items = counts.head(n_top).index.tolist()
    labs = labs[labs["itemid"].isin(top_items)]

    labs["abnormal"] = (labs["flag"] == "abnormal").astype(int)

    means = (
        labs.groupby(["subject_id", "hadm_id", "itemid"])["valuenum"]
        .mean().unstack("itemid")
    )
    means.columns = [f"lab_{c}_mean" for c in means.columns]

    abn = (
        labs.groupby(["subject_id", "hadm_id", "itemid"])["abnormal"]
        .mean().unstack("itemid")
    )
    abn.columns = [f"lab_{c}_abnormal_frac" for c in abn.columns]

    lab_wide = means.join(abn, how="outer").reset_index()

    item_names = d_labitems.set_index("itemid")["label"].to_dict()
    lookup = {iid: item_names.get(iid, f"item_{iid}") for iid in top_items}
    return lab_wide, lookup


def compute_30d_readmission(admissions):
    adm = admissions[["subject_id", "hadm_id", "admittime", "dischtime"]].sort_values(
        ["subject_id", "admittime"]
    )
    adm["next_admittime"] = adm.groupby("subject_id")["admittime"].shift(-1)
    gap_days = (adm["next_admittime"] - adm["dischtime"]).dt.total_seconds() / 86400
    adm["readmit_30d"] = ((gap_days >= 0) & (gap_days <= 30)).astype(int)
    return adm[["subject_id", "hadm_id", "readmit_30d"]]


def make_split(subject_ids, train_frac=TRAIN_FRAC, seed=RANDOM_SEED):
    rng = np.random.default_rng(seed)
    ids = np.array(sorted(subject_ids))
    rng.shuffle(ids)
    n_train = int(len(ids) * train_frac)
    train_ids = set(ids[:n_train])
    return {sid: ("train" if sid in train_ids else "holdout") for sid in ids}


def main():
    patients, admissions, icustays, diagnoses, d_icd_diagnoses, labevents, d_labitems = load_raw()

    age_df = compute_age(patients, admissions)
    base = build_admission_base(admissions, icustays)
    base["ethnicity"] = collapse_ethnicity(base["ethnicity"])

    dx = build_diagnoses_features(diagnoses)
    labs_wide, lab_lookup = build_lab_features(labevents, d_labitems)
    readmit = compute_30d_readmission(admissions)
    gender = patients[["subject_id", "gender"]]

    df = base.merge(age_df, on=["subject_id", "hadm_id"], how="left")
    df = df.merge(gender, on="subject_id", how="left")
    df = df.merge(dx, on=["subject_id", "hadm_id"], how="left")
    df = df.merge(labs_wide, on=["subject_id", "hadm_id"], how="left")
    df = df.merge(readmit, on=["subject_id", "hadm_id"], how="left")

    split_map = make_split(df["subject_id"].unique())
    df["split"] = df["subject_id"].map(split_map)

    df = df.drop(columns=["admittime"], errors="ignore")

    out_path = OUT_DIR / "mimic_demo_clean.csv"
    df.to_csv(out_path, index=False)

    lookup_path = OUT_DIR / "lab_item_lookup.csv"
    pd.Series(lab_lookup, name="label").rename_axis("itemid").reset_index().to_csv(
        lookup_path, index=False
    )

    icd9_lookup_path = OUT_DIR / "icd9_lookup.csv"
    d_icd_diagnoses[["icd9_code", "short_title"]].to_csv(icd9_lookup_path, index=False)

    print(f"Wrote {len(df)} admission rows, {df.shape[1]} columns -> {out_path}")
    print(f"Train/holdout split: {df['split'].value_counts().to_dict()}")
    print(f"Lab item lookup -> {lookup_path}")
    print(f"ICD-9 description lookup -> {icd9_lookup_path}")


if __name__ == "__main__":
    main()