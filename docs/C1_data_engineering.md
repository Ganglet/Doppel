# Data Engineering

**Phase:** Phase 1 — Foundation & Design (Weeks 1–2)
**Owner:** Anoushka (Track 3 / Track C)
**Status:** Complete for Phase 1 scope. Two review gaps (missing ICD-9 lookup, non-JSON list serialization) were found and fixed same-day — see [`problems_and_decisions.md`](problems_and_decisions.md) P-004 and ADR-004.

---

## Objective

Turn the raw MIMIC-III Clinical Database Demo (26 relational tables) into a single clean, admission-level dataset that Track 1's generators can train on and Track 2's evaluation code can score against — with a documented schema, a leakage-safe train/holdout split, and known data-quality issues flagged up front rather than discovered later by whoever consumes the file.

---

## What was built

### Source tables used
Of MIMIC-III's ~26 tables, 7 are loaded — demographics, admissions, ICD-9 codes, and labs, per the blueprint's Stage 1 scope:

```
PATIENTS.csv          -> demographics (SUBJECT_ID, GENDER, DOB)
ADMISSIONS.csv         -> admission events, ethnicity, mortality flag
ICUSTAYS.csv           -> ICU length-of-stay, care unit
DIAGNOSES_ICD.csv      -> ICD-9 codes per admission
D_ICD_DIAGNOSES.csv    -> ICD-9 code -> description lookup
LABEVENTS.csv          -> lab test results
D_LABITEMS.csv         -> lab item ID -> name lookup
```

`CHARTEVENTS`, `NOTEEVENTS`, `MICROBIOLOGYEVENTS`, `PRESCRIPTIONS`, and the rest are out of scope.

### Unit of analysis
One row = one hospital admission (`hadm_id`). This is the grain Track 1 generates at and Track 2 evaluates at.

### Feature engineering
- **Age:** computed from `DOB`/`ADMITTIME`, clipped at 89 with a separate `age_89_plus` flag (ADR-002).
- **Ethnicity:** collapsed to the top 6 raw categories + `OTHER` (raw field has 40+ free-text variants).
- **Diagnoses:** primary ICD-9 code (`seq_num == 1`), full code list (JSON-encoded, ADR-004), and diagnosis count per admission.
- **Labs:** top 20 most-measured lab items (by number of admissions with ≥1 result), pivoted wide into `lab_<ITEMID>_mean` and `lab_<ITEMID>_abnormal_frac` columns.
- **Labels:** `hospital_expire_flag` (in-hospital mortality, from `ADMISSIONS`) and `readmit_30d` (derived via self-join on `subject_id`, admission gap ≤ 30 days).

### Train/holdout split
80/20, split at the `subject_id` level (not `hadm_id`) to prevent the same patient appearing in both splits — see ADR-001. Fixed random seed (42) for reproducibility.

### Known data-quality issues (documented, not hidden)
- Age >89 is shifted to ~300 in the raw data (MIMIC de-identification artifact) — handled per ADR-002.
- Not all admissions have a lab result for every top-20 item — nulls are left as nulls, not silently imputed at this stage.
- With only 100 patients, many ICD-9 codes appear once or not at all — the exact "rare, high-dimensional clinical code" problem the blueprint flags as hard.
- The 80/20 patient-level split can leave a category entirely absent from one split by chance on a small sample — see P-003 for the concrete instance found in `ethnicity`.

---

## Commands

```bash
# 1. Setup: place raw MIMIC-III Demo CSVs in repo root
#    (download: https://physionet.org/content/mimiciii-demo/1.4/, no credentialing needed)
#    PATIENTS.csv, ADMISSIONS.csv, ICUSTAYS.csv, DIAGNOSES_ICD.csv,
#    D_ICD_DIAGNOSES.csv, LABEVENTS.csv, D_LABITEMS.csv

# 2. Install dependencies
pip install pandas numpy

# 3. Run preprocessing
python preprocess_mimic_demo.py

# 4. Verify output
python -c "
import pandas as pd
df = pd.read_csv('output/mimic_demo_clean.csv')
print('shape:', df.shape)
print('split counts:', df['split'].value_counts().to_dict())
"
```

Expected verification output: `shape: (129, 56)`, `split counts: {'train': 94, 'holdout': 35}`.

---

## Key Decisions

**Why split by `subject_id` instead of `hadm_id`?** A patient can have multiple admissions; splitting at the admission level would leak the same patient's signal across train and holdout. See ADR-001.

**Why clip age at 89 instead of using the computed value directly?** MIMIC-III intentionally shifts DOB for patients over 89 as a de-identification step — the raw computed age would be around 300 for these patients. See ADR-002.

**Why pivot only the top 20 lab items instead of all of them?** Raw `LABEVENTS` has hundreds of distinct item IDs; on a 100-patient demo most are too sparse to be useful features. 20 is a starting threshold, documented as revisitable once Track 1/2 see real sparsity numbers in practice.

**Why keep two candidate labels (`hospital_expire_flag`, `readmit_30d`) instead of picking one during preprocessing?** Label selection is Track 2's decision, not Track 3's — see ADR-003 for how and why Track 2 picked `hospital_expire_flag`.

---

## Outputs

| Output | Value |
|---|---|
| Cleaned dataset | `output/mimic_demo_clean.csv` — 129 rows × 56 columns |
| ICD-9 description lookup | `output/icd9_lookup.csv` — 14,567 code→description rows |
| Lab item lookup | `output/lab_item_lookup.csv` — 20 rows |
| Schema documentation | [`schema_and_feature_dictionary.md`](../schema_and_feature_dictionary.md) |
| Train / holdout split | 94 / 35 admissions, seed 42 |
| `icd9_codes` serialization | JSON array string — parse with `json.loads()`, not `ast.literal_eval()` (ADR-004) |
