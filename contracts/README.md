
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