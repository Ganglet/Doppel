# Dataset Validation and Preprocessing Job

**Phase:** Phase 2 — Core Development (Weeks 3–7), commit `21f7b2b` (2026-09-23), branch `track3-phase2-data-validation`, merged as PR #9
**Owner:** Anoushka (Track 3 / Track C). Written up by Rayyan (Track 2) from the repository and the checks below; not yet reviewed by the owner
**Status:** Delivered as files and validated locally. The manifest regenerates byte for byte, and the validator catches all 7 faults it was designed for and passes the committed dataset. The preprocessing Job has not been run, and as written it would look for the raw CSVs in the wrong directory. Evaluation-dataset versioning is Phase 3 and not started.

---

## Objective

Turn Phase 1's one-off preprocessing script into something the pipeline can trust and run as a Job: a machine-readable description of the dataset, checks that fail loudly and gate later stages, paths that work both locally and in a container, and an image and Job that chain the three steps. Phase 1 documented the dataset's known problems in prose ([`C1_data_engineering.md`](C1_data_engineering.md)); this phase makes the checkable ones automatic.

---

## What was built

### 1. Overridable paths and one arithmetic fix

`preprocess_mimic_demo.py` now reads `RAW_DIR` (default `.`) and `OUT_DIR` (default `./output`) from the environment and creates the output directory with `parents=True`, so the same script runs locally and in a container. Age is now computed from year, month and day components instead of datetime subtraction, because MIMIC shifts the date of birth of patients over 89 about 300 years into the past and plain subtraction overflows. The committed dataset is unchanged by this: `output/mimic_demo_clean.csv` is identical to the Phase 1 version.

### 2. Dataset manifest

`generate_manifest.py` writes `output/mimic_demo_clean.manifest.json` for `output/mimic_demo_clean.csv`, in the shape of [`contracts/schemas/dataset.schema.json`](../contracts/schemas/dataset.schema.json).

| Manifest field | Value |
|---|---|
| `dataset_id` | `mimic_demo_clean` |
| `schema_version` | `"1.0"` (a constant in the script) |
| `data_path`, `format` | `output/mimic_demo_clean.csv`, `csv` |
| `columns` | 56 entries of `name`, `dtype` (mapped to `integer`, `float`, `boolean` or `string`) and `nullable` (true if the current data has any null in that column) |

### 3. Validation checks

`validate_dataset.py` validates `output/mimic_demo_clean.csv`, prints `VALIDATION PASSED` or lists every failure, and exits non-zero on failure so it can gate a Job.

| Check | What fails it |
|---|---|
| Contract schema | the manifest doesn't validate against `dataset.schema.json`, or the manifest is missing |
| Required columns | any of 12 identifier, label and core demographic columns is absent |
| Unexpected nulls | any of those 12 columns contains a null (lab columns are allowed nulls) |
| ICD-9 JSON | any `icd9_codes` value fails `json.loads()` (ADR-004) |
| Split values | `split` has a value other than `train` or `holdout`, or lacks either |
| Patient leakage | any `subject_id` appears in both splits (ADR-001) |
| Sanity bounds | age outside [0, 89], negative hospital stay, or a non-binary `hospital_expire_flag` or `readmit_30d` |

### 4. Image and Job

`docker/preprocessing/Dockerfile` builds on `doppel/base:0.1`, copies the three scripts and the dataset schema, and runs `preprocess_mimic_demo.py && generate_manifest.py && validate_dataset.py`. `k8s/jobs/preprocessing-job.yaml` runs it as `doppel-preprocessing` in the `doppel` namespace, mounting a read-only raw-data volume at `/app/raw` and a shared output volume at `/app/output` so downstream Jobs can read the dataset.

### 5. Path decision

Section 6 of [`contracts/README.md`](../contracts/README.md) (2026-09-20) records that the processed dataset lives at `output/mimic_demo_clean.csv`, with its manifest beside it, and not at the `data/processed/` path in the Phase 1 draft.

### Not done, and what the checks found

- **The Job has not been run, and its spec has a gap.** The Job sets no `RAW_DIR`, the script's default is the working directory, and the raw data is mounted at `/app/raw`. Under the Job's environment the script looks for `PATIENTS.csv` in `/app` and fails; I reproduced that locally (`FileNotFoundError: 'PATIENTS.csv'`), and with `RAW_DIR=raw` it proceeds. The two volumes the Job names (`mimic-raw-data-pvc` and `doppel-processed-data-pvc`) are not defined anywhere in `k8s/` (P-017).
- **The validator cannot see class-coverage gaps between splits.** It passes the committed dataset even though `HISPANIC/LATINO - PUERTO RICAN` is in 15 holdout rows and no train rows, which is the gap that invalidated the first attribute-inference attack (P-018).
- **No dataset versioning.** The manifest records `schema_version: "1.0"` but no content hash and no code version. `get_git_commit()` is defined in `generate_manifest.py` and never called. Evaluation-dataset versioning is a Phase 3 task.
- **Missing values are validated, not handled.** The checks confirm nulls occur only where documented; nothing imputes them (see `schema_and_feature_dictionary.md` §5). Track 2's utility pipeline median-imputes downstream.
- **`C1_data_engineering.md` still describes Phase 1 only.** This doc covers Phase 2.

---

## Commands

```bash
# Setup
pip install -r requirements.txt

# Validate the committed dataset (no raw data needed)
python validate_dataset.py

# Rebuild everything from raw MIMIC-III Demo CSVs placed in the repo root
python preprocess_mimic_demo.py && python generate_manifest.py && python validate_dataset.py

# Run against other directories, which is what the Job relies on
RAW_DIR=/path/to/raw OUT_DIR=/path/to/out python preprocess_mimic_demo.py
OUT_DIR=/path/to/out python generate_manifest.py
OUT_DIR=/path/to/out python validate_dataset.py

# Verify: 129 rows, 56 columns, and the manifest regenerates identically
python validate_dataset.py
```

Expected: `VALIDATION PASSED`, 129 rows, 56 columns, all checks green. The container steps (`docker build -f docker/base/Dockerfile -t doppel/base:0.1 .`, then `docker build -f docker/preprocessing/Dockerfile -t doppel/preprocessing:0.1 .`, then `kubectl apply -f k8s/jobs/preprocessing-job.yaml`) were not run.

---

## Key Decisions

**Why environment variables for the paths?** The script's own docstring says it is so the script "runs identically locally and inside a Kubernetes Job".

**Why compute age from components?** The docstring: MIMIC's shifted dates of birth for patients over 89 overflow plain datetime subtraction, and components never overflow.

**Why validate through the manifest against the contract schema?** The validator's docstring lists the contract schema first and says it exits non-zero "so this can gate a CI step or K8s Job", which makes the schema a runtime check and not only a document.

**Why are lab columns excluded from the never-null list?** The validator's comment: labs are expected to be null on a sparse 100-patient demo, per `schema_and_feature_dictionary.md` §5.

**Why `output/` and not `data/processed/`?** Contracts §6: the Phase 1 paths did not match what Tracks 1 and 3 had actually implemented, and Track 1's `--real-csv` and Track 2's code already pointed at `output/mimic_demo_clean.csv`.

---

## Outputs

| Output | Value |
|---|---|
| Cleaned dataset | `output/mimic_demo_clean.csv`, 129 rows × 56 columns, unchanged from Phase 1 |
| Manifest | `output/mimic_demo_clean.manifest.json`, regenerates byte for byte |
| Validator | `validate_dataset.py`, 7 check groups, exits non-zero on failure |
| Image and Job | `docker/preprocessing/Dockerfile`, `k8s/jobs/preprocessing-job.yaml` (not run) |
| Fault-injection evidence | [`dataset_validation_result.md`](dataset_validation_result.md): 7 of 7 designed faults caught, class-coverage gap not caught |
| Open problems | P-017 (Job spec) and P-018 (class coverage) in [`problems_and_decisions.md`](problems_and_decisions.md) |
