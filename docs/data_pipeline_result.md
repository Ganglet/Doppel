# Data Pipeline Result — MIMIC-III Demo preprocessed into a clean, leakage-safe dataset (2026-09-17)

Raw evidence that `preprocess_mimic_demo.py` produces the dataset described in [`schema_and_feature_dictionary.md`](../schema_and_feature_dictionary.md). Reproduce with `python preprocess_mimic_demo.py` (requires raw MIMIC-III Demo CSVs in the repo root — see [`C1_data_engineering.md`](C1_data_engineering.md)).

---

## Method (honest framing)

This validates that the preprocessing script runs against the real MIMIC-III Clinical Database Demo (100 patients) and produces output matching the documented schema — row count, column count, split proportions, and null patterns were all checked directly against the output file, not assumed from reading the script. What this does **not** validate: generalization to the full (non-demo) MIMIC-III database, which has ~40,000 patients instead of 100 and would likely not reproduce the class-coverage gaps documented in [`attribute_inference_result.md`](attribute_inference_result.md) — those are specifically small-sample artifacts.

---

## Results

| Check | Value |
|---|---|
| Source patients | 100 |
| Output rows (admissions) | 129 |
| Output columns | 56 |
| Train / holdout split | 94 / 35 (patient-level, seed 42) |
| Null cells (non-zero columns only) | 6 lab-value cells across `lab_50893_*`, `lab_50960_*`, `lab_50970_*` |
| `icd9_codes` JSON-parse failures | 0 / 129 (verified after the ADR-004 fix) |

---

## Raw evidence

```
$ python -c "
import pandas as pd
df = pd.read_csv('output/mimic_demo_clean.csv')
print('shape:', df.shape)
n = df.isnull().sum()
print(n[n>0])
print('split counts:', df['split'].value_counts().to_dict())
"
shape: (129, 56)
lab_50893_mean             3
lab_50960_mean             2
lab_50970_mean             3
lab_50893_abnormal_frac    3
lab_50960_abnormal_frac    2
lab_50970_abnormal_frac    3
dtype: int64
split counts: {'train': 94, 'holdout': 35}
```

```
$ python -c "
import pandas as pd, json
df = pd.read_csv('output/mimic_demo_clean.csv')
bad = 0
for v in df['icd9_codes'].dropna():
    try: json.loads(v)
    except Exception: bad += 1
print('rows failing json.loads:', bad, '/', df['icd9_codes'].notna().sum())
"
rows failing json.loads: 0 / 129
```

---

## Contrast with the pre-review version

The first committed version of this pipeline (`c7c177a`) shipped without the ICD-9 lookup table and with `icd9_codes` as a non-JSON Python list repr. Both were caught in review and fixed same-day in `6280b0e` — see [`problems_and_decisions.md`](problems_and_decisions.md) P-004 and ADR-004. The numbers above are from the post-fix version.
