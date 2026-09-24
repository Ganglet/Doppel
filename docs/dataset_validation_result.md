# Dataset Validation Result — the validator catches all seven faults it was designed for, and cannot see the class-coverage gap the real data has (2026-09-24)

Raw evidence for `validate_dataset.py`, Track 3's Phase 2 checks ([`C2_data_validation.md`](C2_data_validation.md)). Reproduce by saving the script under Raw evidence as `fault_test.py` in the repo root and running `python fault_test.py`; it changes no repo files.

---

## Method (honest framing)

The script takes the committed `output/mimic_demo_clean.csv`, injects one fault at a time into a copy (a single row, or one column), regenerates the manifest with `generate_manifest.py`, and runs `validate_dataset.py` on it, all in a temporary directory selected with `OUT_DIR`. It also checks whether any categorical level appears in the holdout but never in train.

What this does not show:

- **It tests the checks against faults chosen to match them.** Seven injected faults, each written after reading the validator, so 7 of 7 caught shows the checks work as coded, not that they catch every real data problem.
- **My first attempt at the leakage test was invalid.** I flipped the split of a patient with a single admission, which cannot create leakage, and the validator correctly passed it. The script above picks a patient with two admissions.
- **One dataset only.** These are single-row faults on a 129-row file; larger or subtler corruption was not tried.
- **The preprocessing steps themselves were not re-run.** The raw MIMIC-III files are not in the repository, so this validates the committed output, not the pipeline that produced it.

**Honest phrasing for the report: "the automatic checks catch every fault they were written for, including patient leakage across splits; they do not check whether categorical values in the holdout also occur in train, which is the gap that invalidated the first ethnicity attribute-inference attack."**

---

## Results

| Injected fault | Validator exit code | Message |
|---|---|---|
| none (committed dataset) | 0 | `VALIDATION PASSED`, 129 rows, 56 columns |
| null in a required column | 1 | `Column 'gender' has 1 unexpected null(s)` |
| age above 89 | 1 | `age out of expected [0, 89] bounds` |
| negative hospital stay | 1 | `los_hospital_days has negative values` |
| `icd9_codes` not valid JSON | 1 | `1 row(s) in icd9_codes fail json.loads()` |
| patient in both splits | 1 | `1 subject_id(s) appear in both train and holdout` |
| required column missing | 1 | `Missing required columns: ['readmit_30d']` |
| non-binary label | 1 | `hospital_expire_flag has non-binary values` |

| Class coverage between splits (not checked by the validator) | Levels in holdout but never in train |
|---|---|
| `ethnicity` | `HISPANIC/LATINO - PUERTO RICAN` (15 of 35 holdout rows) |
| `admission_type` | none |
| `first_careunit` | none |
| `gender` | none |

| Reading | Evidence |
|---|---|
| Each designed check fires on the fault it targets | 7 of 7 faults exit 1 with a message naming the fault |
| The committed dataset passes | exit 0, 129 rows, 56 columns |
| The manifest is reproducible | regenerated into a temp directory it is byte-identical to the committed `output/mimic_demo_clean.manifest.json` |
| The validator passes data with a class-coverage gap | the committed dataset passes while `HISPANIC/LATINO - PUERTO RICAN` has 15 holdout rows and 0 train rows |

---

## Raw evidence

```python
import os, subprocess, sys, tempfile
import pandas as pd

base = pd.read_csv("output/mimic_demo_clean.csv")
multi_sid = base.groupby("subject_id").filter(lambda g: len(g) > 1).subject_id.iloc[0]
flip_row = base.index[base.subject_id == multi_sid][0]
flipped = "holdout" if base.loc[flip_row, "split"] == "train" else "train"

faults = {
    "null in a required column":   lambda d: d.__setitem__("gender", d["gender"].where(d.index != 0)),
    "age above 89":                lambda d: d.__setitem__("age", d["age"].where(d.index != 0, 95)),
    "negative hospital stay":      lambda d: d.__setitem__("los_hospital_days", d["los_hospital_days"].where(d.index != 0, -1.0)),
    "icd9_codes not valid JSON":   lambda d: d.__setitem__("icd9_codes", d["icd9_codes"].where(d.index != 0, "['0389']")),
    "patient in both splits":      lambda d: d.__setitem__("split", d["split"].where(d.index != flip_row, flipped)),
    "required column missing":     lambda d: d.drop(columns=["readmit_30d"], inplace=True),
    "non-binary label":            lambda d: d.__setitem__("hospital_expire_flag", d["hospital_expire_flag"].where(d.index != 0, 2)),
}

def validate(df):
    with tempfile.TemporaryDirectory() as out:
        df.to_csv(f"{out}/mimic_demo_clean.csv", index=False)
        env = dict(os.environ, OUT_DIR=out)
        subprocess.run([sys.executable, "generate_manifest.py"], env=env, capture_output=True)
        r = subprocess.run([sys.executable, "validate_dataset.py"], env=env, capture_output=True, text=True)
    return r.returncode, (r.stderr or r.stdout).strip().splitlines()

rc, msg = validate(base)
print(f"{'committed dataset (no fault)':28s} exit {rc}  {msg[-1][:60].encode('ascii','replace').decode()}")
for name, mutate in faults.items():
    df = base.copy()
    mutate(df)
    rc, msg = validate(df)
    print(f"{name:28s} exit {rc}  {msg[1].strip()[:70].encode('ascii','replace').decode() if rc else 'NOT CAUGHT'}")

train, holdout = base[base.split == "train"], base[base.split == "holdout"]
for col in ("ethnicity", "admission_type", "first_careunit", "gender"):
    missing = sorted(set(holdout[col]) - set(train[col]))
    rows = int(holdout[col].isin(missing).sum())
    print(f"levels in holdout but never in train, {col}: {missing or 'none'} ({rows} holdout rows)")
```

```
$ python fault_test.py
committed dataset (no fault) exit 0  VALIDATION PASSED ? 129 rows, 56 columns, all checks green.
null in a required column    exit 1  - Column 'gender' has 1 unexpected null(s) ? this column must never be
age above 89                 exit 1  - age out of expected [0, 89] bounds
negative hospital stay       exit 1  - los_hospital_days has negative values
icd9_codes not valid JSON    exit 1  - 1 row(s) in icd9_codes fail json.loads() ? must be valid JSON per AD
patient in both splits       exit 1  - 1 subject_id(s) appear in both train and holdout ? split leakage
required column missing      exit 1  - Missing required columns: ['readmit_30d']
non-binary label             exit 1  - hospital_expire_flag has non-binary values
levels in holdout but never in train, ethnicity: ['HISPANIC/LATINO - PUERTO RICAN'] (15 holdout rows)
levels in holdout but never in train, admission_type: none (0 holdout rows)
levels in holdout but never in train, first_careunit: none (0 holdout rows)
levels in holdout but never in train, gender: none (0 holdout rows)
```

The `?` characters are the validator's em-dash, replaced by the script's ASCII conversion for a Windows console.

```
$ mkdir -p /tmp/val && cp output/mimic_demo_clean.csv /tmp/val/
$ OUT_DIR=/tmp/val python generate_manifest.py
Wrote manifest for 129 rows, 56 columns -> /tmp/val/mimic_demo_clean.manifest.json
$ cmp /tmp/val/mimic_demo_clean.manifest.json output/mimic_demo_clean.manifest.json && echo identical
identical
```

---

## Contrast with the Phase 1 checks

[`data_pipeline_result.md`](data_pipeline_result.md) verified the same properties by hand-typed commands (shape, null pattern, split counts, JSON parse). The validator makes those checks automatic and adds patient-leakage, bounds and contract-schema checks, but it inherits the same blind spot: Phase 1's known-issues list already named the sparse ethnicity split, and nothing checks for it.
