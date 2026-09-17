# Doppel — Data Schema & Feature Dictionary
**Track 3 · Data Engineering · Phase 1 deliverable**

## 1. Source
MIMIC-III Clinical Database **Demo v1.4** (PhysioNet, open access, no credentialing required).
- 100 patients, all with a recorded date of death (by demo selection criteria), not necessarily during
  the captured admission/ICU stay.
- Same relational schema as full MIMIC-III, minus free-text `NOTEEVENTS`.
- Download: https://physionet.org/content/mimiciii-demo/1.4/ (zip of CSVs, no login needed).

## 2. Source tables used
Doppel only needs a subset of the 26 MIMIC-III tables — demographics, admissions, ICD-9 codes, and labs,
per the blueprint's Stage 1 definition.

| Table | Purpose | Key columns used |
|---|---|---|
| `PATIENTS.csv` | Demographics | `SUBJECT_ID`, `GENDER`, `DOB`, `DOD` |
| `ADMISSIONS.csv` | Hospital admission events | `SUBJECT_ID`, `HADM_ID`, `ADMITTIME`, `DISCHTIME`, `ADMISSION_TYPE`, `HOSPITAL_EXPIRE_FLAG`, `ETHNICITY` |
| `ICUSTAYS.csv` | ICU stay events | `SUBJECT_ID`, `HADM_ID`, `ICUSTAY_ID`, `FIRST_CAREUNIT`, `LOS` |
| `DIAGNOSES_ICD.csv` | ICD-9 diagnosis codes per admission | `SUBJECT_ID`, `HADM_ID`, `ICD9_CODE`, `SEQ_NUM` |
| `D_ICD_DIAGNOSES.csv` | ICD-9 code → description lookup | `ICD9_CODE`, `SHORT_TITLE` |
| `LABEVENTS.csv` | Lab test results | `SUBJECT_ID`, `HADM_ID`, `ITEMID`, `VALUENUM`, `FLAG` |
| `D_LABITEMS.csv` | Lab item ID → name lookup | `ITEMID`, `LABEL` |

Not used: `CHARTEVENTS`, `NOTEEVENTS`, `MICROBIOLOGYEVENTS`, `PRESCRIPTIONS`, and other tables outside the
blueprint's stated scope (demographics, ICD-9, labs, admissions).

## 3. Unit of analysis
One row = **one hospital admission** (`HADM_ID`). This is the grain Track 1's generators will model and
Track 2 will evaluate on — agree this with Track 1/2 before generation work starts, since it fixes the
interface contract for Stage 2.

## 4. Output feature dictionary

| Feature | Type | Source | Notes |
|---|---|---|---|
| `subject_id` | int | PATIENTS | patient identifier, kept for join integrity only — drop before modeling |
| `hadm_id` | int | ADMISSIONS | admission identifier — drop before modeling |
| `age` | int | PATIENTS.DOB, ADMISSIONS.ADMITTIME | age at admission; ages >89 are shifted in MIMIC-III (median ~91.4) — cap/flag per §5 |
| `gender` | categorical (M/F) | PATIENTS | |
| `ethnicity` | categorical | ADMISSIONS | collapse to top N categories + "OTHER" (raw field has 40+ free-text variants) |
| `admission_type` | categorical | ADMISSIONS | EMERGENCY / ELECTIVE / URGENT / NEWBORN |
| `los_hospital_days` | float | ADMISSIONS | (DISCHTIME − ADMITTIME) in days |
| `los_icu_days` | float | ICUSTAYS | from `LOS` column, summed if multiple ICU stays per admission |
| `first_careunit` | categorical | ICUSTAYS | first ICU unit type |
| `icd9_codes` | list[str] | DIAGNOSES_ICD | all codes for the admission, ordered by `SEQ_NUM` |
| `icd9_primary` | str | DIAGNOSES_ICD | code with `SEQ_NUM == 1` |
| `n_diagnoses` | int | DIAGNOSES_ICD | count of codes per admission |
| `lab_<ITEMID>_mean` | float | LABEVENTS | mean value per common lab item, pivoted wide (see §6) |
| `lab_<ITEMID>_abnormal_frac` | float | LABEVENTS | fraction of that lab's results flagged abnormal |
| `hospital_expire_flag` | binary | ADMISSIONS | in-hospital mortality — candidate downstream-utility label (Track 2) |
| `readmit_30d` | binary | derived (ADMISSIONS, self-join) | 30-day readmission flag — alternate downstream-utility label |

## 5. Known data-quality issues to handle in preprocessing
- **Age >89 shifted to ~300 in raw data** (MIMIC de-identification artifact for HIPAA compliance) —
  clip or bucket these into an "89+" category rather than treating as a real age.
- **Missing DOD** for patients who didn't die in-hospital and weren't followed post-discharge — not
  all rows will have every field; don't assume no-nulls.
- **`LABEVENTS` is admission-level, not encounter-level** for some tests — a lab drawn before formal
  admission may have `HADM_ID` null; drop or attribute to nearest admission by timestamp, decide once
  and document it (interface contract).
- **ICD-9 code sparsity**: with only 100 patients, many rare codes will appear once or not at all —
  this is exactly the "rare, high-dimensional clinical code" problem the blueprint flags as hard, so
  don't silently drop rare codes — flag frequency in the schema doc for Track 1/2's awareness.

## 6. Lab feature selection
Raw `LABEVENTS` has hundreds of distinct `ITEMID`s; most are too sparse in a 100-patient demo to be
useful features. Preprocessing selects the **top 20 most frequently measured lab items** (by number of
admissions with ≥1 result) and pivots them wide into `lab_<ITEMID>_mean` / `_abnormal_frac` columns.
This threshold (20) is a starting point — revisit with Track 1/2 once you see real sparsity numbers.

## 7. Train / held-out split
- Split at the **`SUBJECT_ID`** level, not the admission level, to avoid leaking the same patient across
  train and held-out sets (a patient can have multiple admissions).
- Given only 100 patients: 80/20 split → ~80 train patients, ~20 held-out patients.
- Fixed random seed (42) for reproducibility, per the blueprint's reproducibility goal.
- Held-out set is reserved for Track 2's utility evaluation (train-on-synthetic / test-on-real) — the
  generators (Track 1) should only ever see the train split.

## 8. Interface contract (output of this stage)
Preprocessing outputs three files in `output/`:
- `mimic_demo_clean.csv` — one row per admission, columns as in §4, plus a `split` column
  (`train` / `holdout`). This is the file Track 1 trains generators on (train rows only) and Track 2
  evaluates against (both splits).
- `lab_item_lookup.csv` — maps `lab_<ITEMID>_*` columns back to human-readable lab names.
- `icd9_lookup.csv` — maps `icd9_code` values (in `icd9_primary` and `icd9_codes`) to short text
  descriptions, sourced from `D_ICD_DIAGNOSES.csv`. Needed for the report and for readable model output.

**`icd9_codes` format:** this column is a JSON-encoded list (e.g. `[4019, 2724]`), not a Python literal —
parse it with `json.loads()`, not `ast.literal_eval()` or manual string parsing.

Confirm this contract with Track 1/2/4 before Phase 2 starts.