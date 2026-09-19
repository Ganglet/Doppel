# Project Doppel

**A distributed pipeline for benchmarking synthetic EHR generators on fidelity, utility, and privacy — under one dataset, one protocol, one environment.**

![Python](https://img.shields.io/badge/python-3.11-blue)
![Status](https://img.shields.io/badge/status-phase%201%20of%204-yellow)
![CI](https://img.shields.io/badge/CI-not%20configured-lightgrey)
![License](https://img.shields.io/badge/license-MIT%20code%20%7C%20ODbL%20data-blue)
![Dataset](https://img.shields.io/badge/dataset-MIMIC--III%20Demo-blueviolet)

---

## What this is

Doppel trains three families of synthetic Electronic Health Record generators — a statistical baseline, a GAN-family model (CTGAN/TVAE), and a tabular diffusion model — on the MIMIC-III Clinical Database Demo, then scores each one on the same fidelity, downstream-utility, and privacy-attack protocol so the three are actually comparable instead of three incomparable sets of numbers. **The evaluation harness (fidelity, utility, membership-inference, and attribute-inference code) is built and self-validated end-to-end** — it correctly distinguishes a memorizing stand-in generator (0.824 membership-inference AUROC) from a noisy one (0.663 AUROC) before any real generator exists to test it on.

> **Status:** Phase 1 of 4 (Weeks 1–2 of a 14-week plan). Data engineering and evaluation tracks are done for this phase. Generative modeling has its Phase 1 generator contract and statistical baseline in place, and Kubernetes orchestration has not started. Results 2–4 were produced by running the evaluation code against **real data used as a synthetic-data stand-in**. Result 5 is the first real synthetic data, from the statistical baseline only; CTGAN/TVAE and the diffusion model don't exist yet.

---

## Architecture

```mermaid
flowchart LR
    subgraph T3["Track 3 — Data Engineering (done)"]
        RAW[("MIMIC-III Demo CSVs\n100 patients")] --> PREP["preprocess_mimic_demo.py"]
        PREP --> CLEAN[["mimic_demo_clean.csv\n129 admissions x 56 cols"]]
        PREP --> ICD[["icd9_lookup.csv"]]
        PREP --> LAB[["lab_item_lookup.csv"]]
    end

    subgraph T1["Track 1 — Generation (contract + statistical baseline done)"]
        CLEAN -. train split .-> GEN{{"statistical / CTGAN-TVAE / diffusion"}}
        GEN -.-> SYN[("synthetic.csv")]
    end

    subgraph T2["Track 2 — Evaluation (done, self-tested)"]
        CLEAN -- holdout split --> FID["fidelity_metrics.py"]
        CLEAN -- "train split (stand-in)" --> UTIL["utility_eval.py"]
        CLEAN -- "train split (stand-in)" --> MIA["membership_inference.py"]
        CLEAN -- "train split (stand-in)" --> ATTR["attribute_inference.py"]
        SYN -. "real input, pending" .-> FID
        SYN -.-> UTIL
        SYN -.-> MIA
        SYN -.-> ATTR
    end

    subgraph T4["Track 4 — Aggregation (not started)"]
        FID --> DASH[["dashboard / Pareto frontier"]]
        UTIL --> DASH
        MIA --> DASH
        ATTR --> DASH
    end

    style RAW fill:#e0e0e0,stroke:#999
    style CLEAN fill:#8fd19e,stroke:#2e7d32
    style ICD fill:#8fd19e,stroke:#2e7d32
    style LAB fill:#8fd19e,stroke:#2e7d32
    style GEN fill:#f5f5f5,stroke:#999,stroke-dasharray: 5 5
    style SYN fill:#f5f5f5,stroke:#999,stroke-dasharray: 5 5
    style FID fill:#8fd19e,stroke:#2e7d32
    style UTIL fill:#8fd19e,stroke:#2e7d32
    style MIA fill:#8fd19e,stroke:#2e7d32
    style ATTR fill:#8fd19e,stroke:#2e7d32
    style DASH fill:#f5f5f5,stroke:#999,stroke-dasharray: 5 5
```

The evaluation stage (green) is fully wired and validated using the real holdout split as a synthetic-data stand-in — the dashed edges show exactly where real generator output will plug in later with no code changes. The generation and aggregation stages (grey, dashed) are the two pieces that don't exist yet, so right now the pipeline has a working middle with no ends attached.

---

## The problem

Hospitals want to share patient data for research without violating privacy, and synthetic data generation is the usual answer — but published evaluations of synthetic EHR generators are inconsistent: different studies use different attack models and different downstream tasks, so results can't be compared across papers. That fragmentation is concrete, not abstract: building this pipeline's own attribute-inference test on a 100-patient, 129-admission demo dataset immediately produced a 43% single-class skew in the holdout split (`HISPANIC/LATINO - PUERTO RICAN` — 15 of 35 holdout admissions, 0 of 94 train admissions), a direct instance of the small-sample, rare-category problem the literature flags as unresolved for high-dimensional clinical data. Doppel fixes one dataset, one protocol, and one environment so the three generator families are graded on identical, reproducible terms.

---

## How it works

| Layer | What it does |
|---|---|
| Data Prep (Track 3) | Loads 7 MIMIC-III Demo tables, builds one row per hospital admission (demographics, labs, ICD-9 codes, LOS), splits 80/20 by patient to avoid leakage, and writes a single clean CSV plus two lookup tables. |
| Generation (Track 1) | Encodes the `train` split into one shared 110-column modeling frame (ICD-9 codes as multi-hot plus a rare-code tail), fits a generator on it, and decodes the samples back to the exact schema of the cleaned CSV. Every output is checked against a written contract before it's saved. The statistical baseline (Gaussian copula) is built; CTGAN/TVAE and the diffusion model come in Phase 2. |
| Evaluation (Track 2) | Scores any dataset matching that schema on fidelity (JS divergence, correlation preservation, KS tests), downstream utility (train-on-synthetic/test-on-real AUROC), and privacy (shadow-model membership inference, attribute inference). |
| Aggregation (Track 4) | *Not built yet.* Will collect all evaluation output and render the fidelity–utility–privacy Pareto frontier on a dashboard. |

---

## Results

### 1. Clean, leakage-safe dataset (Track 3)

| Stage | Value |
|---|---|
| Source | MIMIC-III Clinical Database Demo v1.4, 100 patients |
| Output rows | 129 hospital admissions |
| Output columns | 56 |
| Train / holdout split | 94 / 35 admissions, split by `subject_id` (patient-level, not admission-level) |
| Random seed | 42 (fixed, documented) |

> **Honest scope:** this is real data, cleaned — no synthetic data exists yet. The patient-level split is leakage-safe but, on only 100 patients, produces the ethnicity skew described above. See [`schema_and_feature_dictionary.md`](schema_and_feature_dictionary.md) for the full known-issues list.

### 2. Fidelity metrics — implemented and self-tested

Measured real `train` split vs. real `holdout` split (i.e. the harness's own noise floor, not any generator's fidelity):

| Metric | Value | Protocol threshold |
|---|---|---|
| Mean Jensen–Shannon divergence (49 columns) | 0.1001 | ≤ 0.10 good, ≤ 0.20 acceptable |
| Correlation preservation (mean abs. diff) | 0.2025 | ≤ 0.10 good, ≤ 0.20 acceptable |
| KS test pass fraction (p ≥ 0.05) | 65.22% | reported, not gated |

> **Note:** these numbers measure real-vs-real sampling noise on a 94/35 split, not a generator's fidelity to real data. The correlation-preservation figure landing right at the edge of "acceptable" is itself informative — it shows how much apparent fidelity loss this dataset's small sample size alone produces, before any generator is even involved.

### 3. Downstream utility pipeline (TRTR vs. TSTR) — implemented and self-tested

| Classifier | TRTR AUROC (5-fold CV, real train) | TSTR AUROC (stand-in "synthetic" → real holdout) | Gap |
|---|---|---|---|
| Logistic Regression | 0.5778 | 0.4885 | 0.0893 |
| Random Forest | 0.7373 | 0.8851 | −0.1478 |

> **Honest scope:** "TSTR" here trains on the real `train` split standing in for synthetic data, so this validates the pipeline's plumbing (feature encoding, imputation, scaling, AUROC scoring), not any generator's utility preservation. The Random Forest's TSTR score beating its own TRTR baseline is a symptom of that stand-in setup (small holdout, single train/test draw), not evidence that a generator works. Full protocol: [`eval_protocol.md`](eval_protocol.md#3-downstream-utility-metric).

### 4. Privacy attacks — implemented and self-validated

**Membership inference** (shadow-model attack, 8 shadow models, leave-one-shadow-out evaluation):

| Stand-in generator | Attack AUROC | Interpretation |
|---|---|---|
| Memorizing (noise_scale = 0.0) | 0.8237 | Harness correctly detects strong membership leakage |
| Noisy (noise_scale = 0.3) | 0.6630 | Harness correctly shows leakage drops with added noise |

**Attribute inference** (target: `ethnicity`, attacker = Random Forest trained on stand-in "synthetic" data):

| Metric | Value |
|---|---|
| Attacker accuracy | 0.5143 |
| Base-rate accuracy (majority class) | 0.5143 |
| Uplift | 0.0000 |

> **Note:** the 0.0000 uplift is not evidence of good privacy — it's because the attacker never saw the `HISPANIC/LATINO - PUERTO RICAN` class in training (0 of 94 train rows) and predicted the majority class every time. This is a documented data-split artifact, not a generator property. See [`eval_protocol.md`](eval_protocol.md#attribute-inference-implemented--attribute_inferencepy) for the full writeup.

### 5. Statistical baseline generator (Track 1): first real synthetic data

Gaussian copula and the independent-marginals reference floor, fit on the 94 train rows and scored with Track 2's unmodified fidelity and utility code:

| Arm | Mean JSD vs train | Corr. diff vs train | TSTR AUROC, LR (20 seeds) | TSTR AUROC, RF (20 seeds) |
|---|---|---|---|---|
| `independent_marginals` (floor) | 0.017 | 0.160 | 0.468 ± 0.196 | 0.537 ± 0.181 |
| `gaussian_copula` | 0.016 | 0.139 | 0.559 ± 0.239 | 0.555 ± 0.172 |

> **Honest scope:** both outputs pass the generator contract and reproduce byte for byte from their seed. The copula preserves more correlation than the floor, but its utility lead sits inside a seed-to-seed spread of about 0.2 AUROC. On a single seed, the floor, which has no feature-label signal at all, scored above the TRTR ceiling. That's why generators are reported over seeds (ADR-012). Full writeup, including three caveats on the current metrics: [`docs/baseline_generator_result.md`](docs/baseline_generator_result.md).

---

## Honest limitations

- **Only the statistical baseline exists.** CTGAN/TVAE and the diffusion model are Phase 2 builds. Results 2–4 validate the evaluation code, and Result 5 is the first (baseline-only) synthetic data.
- **The modeling frame is wider than the data.** 110 modeled columns against 94 training rows (d > n) means any flexible generator can memorize the training set.
- **No orchestration exists yet.** Track 4's Docker/Kubernetes pipeline and dashboard haven't started — the project is currently 6 standalone Python scripts run manually, not the containerized system the blueprint describes.
- **The demo dataset is small and skewed.** 100 patients produces a train/holdout split where at least one ethnicity category is entirely absent from `train` — this affects attribute-inference validity and will likely affect Track 1's generator training too.
- **6 lab-value cells are null** across 3 lab columns (Calcium, Magnesium, Phosphate); the utility pipeline median-imputes them, but that choice hasn't been validated against alternatives.
- **No automated test suite.** Validation so far is manual script runs plus printed sanity checks (e.g. the memorizing-vs-noisy membership-inference comparison), not `pytest` coverage.
- **No CI/CD.** Nothing runs automatically on push.
- **This is a course project** (Big Data Analysis) on a 14-week plan started 2026-09-17 — scope and deadlines may still shift.

---

## Repository structure

```
.
├── Doppel_Blueprint.pdf              # original project spec: architecture, phases, tracks
├── preprocess_mimic_demo.py          # Track 3: raw MIMIC-III Demo CSVs -> cleaned admission-level dataset
├── schema_and_feature_dictionary.md  # Track 3: data schema, feature dictionary, known data-quality issues
├── eval_protocol.md                  # Track 2: fidelity/utility/privacy formulas and thresholds
├── fidelity_metrics.py               # Track 2: JS divergence, correlation preservation, KS tests
├── utility_eval.py                   # Track 2: train-on-synthetic / test-on-real utility pipeline
├── membership_inference.py           # Track 2: shadow-model membership-inference attack
├── attribute_inference.py            # Track 2: attribute-inference attack
├── generators/                       # Track 1: generator contract, shared codec, validator, baselines
│   ├── codec.py                      #   real CSV <-> the 110-column modeling frame all generators share
│   ├── copula.py                     #   Gaussian copula baseline + independent-marginals floor
│   ├── validate.py                   #   Stage 2 output-contract checker
│   └── generate.py                   #   Stage 2 entry point (fit, sample, decode, validate, write)
├── output/
│   ├── mimic_demo_clean.csv          # cleaned dataset (129 admissions x 56 cols)
│   ├── icd9_lookup.csv               # ICD-9 code -> description lookup (14,567 codes)
│   ├── lab_item_lookup.csv           # lab item ID -> name lookup (top 20 labs)
│   └── synthetic/                    # generator output + manifests (regenerated from seed, not committed)
├── LICENSE                           # MIT, for the code
├── DATA_LICENSE.md                   # ODbL 1.0, for MIMIC-III-derived data
└── .gitignore                        # excludes raw MIMIC-III source tables, venv, generated data
```

Track 4 (`orchestration/`, `dashboard/`) directories don't exist yet — they'll be added when that work starts.

---

## Quick start

The cleaned dataset is already committed, so you can see real evaluation output with zero external downloads and no cloud account:

```bash
git clone https://github.com/Ganglet/Doppel.git
cd Doppel
pip install pandas==2.3.3 numpy scikit-learn==1.8.0 scipy==1.17.1

python fidelity_metrics.py       # JS divergence / correlation / KS report
python utility_eval.py           # TRTR vs TSTR AUROC
python membership_inference.py   # shadow-model attack sanity check
python attribute_inference.py    # attribute-inference attack

python -m generators.generate --generator gaussian_copula --seed 42   # statistical baseline
python -m generators.validate output/synthetic/gaussian_copula_seed42.csv
```

---

## Reproduce everything else

```bash
# Regenerate the cleaned dataset from raw source (requires manual PhysioNet download —
# MIMIC-III Clinical Database Demo v1.4, no credentialing required:
# https://physionet.org/content/mimiciii-demo/1.4/)
# Place PATIENTS.csv, ADMISSIONS.csv, ICUSTAYS.csv, DIAGNOSES_ICD.csv,
# D_ICD_DIAGNOSES.csv, LABEVENTS.csv, D_LABITEMS.csv in the repo root, then:
python preprocess_mimic_demo.py
```

```bash
# Staging / production / cloud deployment
# [TODO: not applicable yet — Track 4's Docker/Kubernetes orchestration hasn't started]
```

---

## Operational safety

No cloud resources are in use yet — the pipeline is designed to run entirely on a local Kubernetes cluster (minikube/kind) once Track 4 builds it, so there's no cost-teardown concern at this stage. The one safety practice already in place: raw MIMIC-III source tables are excluded via [`.gitignore`](.gitignore) (added 2026-09-17, in the same commit that fixed a data-serialization bug flagged in review), so re-running preprocessing locally never risks committing patient-level source data to a public repository.

---

## Roadmap

| Phase (Weeks) | Track 1 — Generative Modeling | Track 2 — Evaluation | Track 3 — Data Engineering | Track 4 — Systems & Delivery |
|---|---|---|---|---|
| Phase 1 (1–2) | ✅ Generator contract, shared codec, validator, statistical baseline | ✅ Protocol defined, task selected | ✅ Cleaned dataset, schema, `.gitignore` | Not started |
| Phase 2 (3–7) | Not started | ✅ Fidelity/utility/privacy code (self-tested on stand-in data) | — | Not started |
| Phase 3 (8–11) | Not started | Blocked on Track 1 output | — | Not started |
| Phase 4 (12–14) | Not started | Not started | Not started | Not started |

---

## Authors

- **Angshuman** — Track 1, Generative Modeling Core (statistical baseline, CTGAN/TVAE, diffusion model; cross-track architecture decisions)
- **Rayyan** (GitHub: Rayyan-mohammed) — Track 2, Privacy & Utility Evaluation (fidelity, utility, and privacy-attack modules; evaluation protocol)
- **Anoushka** (GitHub: AnoushkaSarkar) — Track 3, Data Engineering (MIMIC-III preprocessing, schema, feature dictionary)
- **Anshuman CE** — Track 4, Systems Integration & Delivery (containerization, Kubernetes orchestration, dashboard, final delivery) — not yet started

---

## Documentation index

- [`Doppel_Blueprint.pdf`](Doppel_Blueprint.pdf) — original project spec: architecture, 4 phases, track ownership, success criteria
- [`schema_and_feature_dictionary.md`](schema_and_feature_dictionary.md) — full data schema, feature dictionary, known data-quality issues
- [`eval_protocol.md`](eval_protocol.md) — fidelity/utility/privacy formulas, thresholds, and the ethnicity-split caveat
- [`docs/A1_generative_modeling.md`](docs/A1_generative_modeling.md) — Track 1: generator contract, modeling frame, ICD-9 encoding, diffusion design, literature review
- [`docs/baseline_generator_result.md`](docs/baseline_generator_result.md) — first synthetic data: contract self-tests, fidelity, 20-seed utility, metric caveats
- [`LICENSE`](LICENSE) / [`DATA_LICENSE.md`](DATA_LICENSE.md) — MIT for code, ODbL 1.0 for MIMIC-III-derived data
