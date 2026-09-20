
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