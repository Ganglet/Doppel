"""Column roles and file paths for the generation stage. Single source of truth for Track 1's contract."""

from pathlib import Path

import pandas as pd

REAL_CSV = Path("output/mimic_demo_clean.csv")
SYNTH_DIR = Path("output/synthetic")

ID_COLS = ["subject_id", "hadm_id"]
SPLIT_COL = "split"
TRAIN_SPLIT = "train"
SYNTH_SPLIT = "synthetic"

CODES_COL = "icd9_codes"
PRIMARY_COL = "icd9_primary"
N_DIAG_COL = "n_diagnoses"

CATEGORICAL = ["admission_type", "ethnicity", "first_careunit", "gender", PRIMARY_COL]
BINARY = ["hospital_expire_flag", "readmit_30d", "age_89_plus"]
INTEGER = ["age"]

AGE_COL = "age"
AGE_FLAG_COL = "age_89_plus"
AGE_CAP = 89

# Surrogate IDs start far above MIMIC-III's ranges so a synthetic ID can never collide with a real one.
SYNTH_SUBJECT_BASE = 10_000_000
SYNTH_HADM_BASE = 20_000_000


def load_real(path=REAL_CSV) -> pd.DataFrame:
    # icd9_primary must stay a string: '0389' (septicemia) read as int becomes 389, a different code.
    return pd.read_csv(path, dtype={PRIMARY_COL: str})


def continuous_cols(df: pd.DataFrame) -> list[str]:
    return [c for c in df.columns if c.startswith("los_") or c.startswith("lab_")]


def lab_ids(df: pd.DataFrame) -> list[str]:
    return [c[len("lab_"):-len("_mean")] for c in df.columns if c.startswith("lab_") and c.endswith("_mean")]


def lab_pair(item_id: str) -> tuple[str, str]:
    return f"lab_{item_id}_mean", f"lab_{item_id}_abnormal_frac"
