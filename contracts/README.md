
# Project Doppel — Integration Contracts

## 1. Data directories

- Raw input data:
  data/raw/

- Processed dataset:
  data/processed/

- Synthetic datasets:
  data/synthetic/

- Evaluation data:
  data/evaluation/

- Final results:
  results/

## 2. Pipeline ownership

Track 3:
- Produces cleaned and validated datasets.

Track 1:
- Reads processed data.
- Produces synthetic datasets.

Track 2:
- Reads synthetic and real evaluation data.
- Produces evaluation metrics.

Track 4:
- Collects results.
- Provides Kubernetes orchestration and aggregation.

## 3. General file format

- Tabular datasets: CSV
- Metadata: JSON.
- Evaluation results: JSON.
- All paths are relative to the pipeline's shared data root.

## 4. Contract status

This document is a Phase 1 draft.
All tracks must review and approve the final schemas
before implementation.

## 5. Track 1 review (2026-09-19)

Status: `generator_output.schema.json` approved with amendments. Section 1 paths still need a decision.

- **`generator_output.schema.json` amended** (ADR-022). `generator_name` now lists the generators that actually exist
  (`gaussian_copula`, `independent_marginals`, `ctgan`, `tvae`, `tabular_diffusion`). `statistical_baseline` became
  `gaussian_copula` and `independent_marginals` was added as the reference floor. `seed` is now required,
  because results are reported over seeds (ADR-012). `hyperparams`, `train_rows`, `train_csv_sha256`, `codec`,
  `git_commit` and `created_utc` are declared. `additionalProperties: false` still holds. Every manifest written by
  `python -m generators.generate` validates against it.
- **Paths in Section 1 don't match the repo yet.** Track 3 writes `output/mimic_demo_clean.csv` and Track 1 writes
  `output/synthetic/`, not `data/processed/` and `data/synthetic/`. Track 1 doesn't depend on either layout:
  `generate` takes `--real-csv` and `--out-dir`, and `validate` takes `--real-csv`, so a Job can mount any data
  root. Track 3 and Track 4 should pick one layout.
- **Generator image:** the base image's root `requirements.txt` is enough for `gaussian_copula` and
  `independent_marginals`. CTGAN, TVAE and the diffusion model add `generators/requirements-neural.txt` (torch, ctgan,
  rdt), which was verified on Python 3.11.5 with the root pins. Install torch from the CPU index. No Python version
  change is needed (ADR-023).

  ## 6. Track 3 / Track 4 path decision (2026-09-20)

Section 1's `data/processed/` and `data/synthetic/` paths do not match what Track 1 and Track 3 actually
implemented. Resolved as follows:

- **Processed dataset lives at `output/mimic_demo_clean.csv`**, not `data/processed/`. Track 3's
  preprocessing pipeline (`preprocess_mimic_demo.py`) writes here, and this is the path Track 1's
  `--real-csv` flag and Track 2's evaluation code should point at.
- **A machine-readable manifest accompanies it** at `output/mimic_demo_clean.manifest.json`, generated
  by `generate_manifest.py` and validated against `contracts/schemas/dataset.schema.json`. Any
  track reading the dataset can use this to confirm columns/dtypes without parsing the CSV first.
- **Synthetic datasets remain at `output/synthetic/`** per Track 1's note above — `data/synthetic/` in
  Section 1 is superseded.
- In a Kubernetes Job (see `k8s/jobs/preprocessing-job.yaml`), the raw-data mount path is configurable
  via the `RAW_DIR` environment variable (defaults to the working directory locally), and output path via
  `OUT_DIR` (defaults to `./output`) — so the same script runs identically local vs. in-cluster.

Section 1's `data/processed/` and `data/synthetic/` should be treated as superseded by this section; a
future pass can update Section 1 directly rather than leaving two conflicting statements in this file.