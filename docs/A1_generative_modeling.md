# Generative Modeling Core

**Phase:** Phase 1 — Foundation & Design (Weeks 1–2)
**Owner:** Angshuman (Track 1 / Track A)
**Status:** Phase 1 scope complete. The generator contract, shared codec, contract validator, and statistical baseline are built and tested. CTGAN/TVAE and the diffusion generator are Phase 2 builds on this interface. See [`problems_and_decisions.md`](problems_and_decisions.md) ADR-008 to ADR-012.

---

## Objective

Define one interface that all three generator families train and sample through, so the benchmark compares generators rather than preprocessing choices, and ship the statistical baseline as the first generator on it. The contract had to come before any model work: Track 2 consumes the output, Track 4 containerizes it, and the blueprint's comparability claim falls apart if each generator encodes the data its own way.

---

## What was built

### Generator package

```
generators/
  schema.py     column roles, paths, surrogate-ID ranges; load_real() reads icd9_primary as str
  codec.py      FrameCodec: real CSV <-> the 110-column modeling frame every generator trains on
  base.py       Generator interface: fit(frame, spec, rng) / sample(n, rng)
  copula.py     Gaussian copula baseline + independent-marginals reference floor
  validate.py   Stage 2 contract checker (CLI, and check_contract() for import)
  generate.py   Stage 2 entry point: fit on train, sample, decode, validate, write CSV + manifest
```

### The modeling frame

The codec turns the 94 train admissions into one 110-column frame with no missing values. Every generator fits on this exact frame and is decoded by the same code.

| Kind | Columns | Count |
|---|---|---|
| categorical | `admission_type`, `ethnicity`, `first_careunit`, `gender`, `icd9_primary` | 5 |
| binary | `hospital_expire_flag`, `readmit_30d`, `age_89_plus` | 3 |
| binary | `miss_<itemid>` missingness flags for the 3 labs with gaps in train | 3 |
| binary | `icd_<code>` multi-hot, one per secondary code in ≥ 5 train admissions | 55 |
| integer | `age`, `n_tail_codes` | 2 |
| continuous | `los_hospital_days`, `los_icu_days`, 40 lab columns | 42 |

Dropped before modeling and rebuilt on decode: `subject_id`, `hadm_id`, `split`, `icd9_codes`, `n_diagnoses`.

110 modeled columns against 94 training rows means d > n. That's the defining constraint for every generator in this project. Any model flexible enough to fit this frame well is flexible enough to memorize it.

### ICD-9 codes (ADR-009)

- **Primary code:** a categorical column (65 levels in train, 50 of them singletons).
- **Frequent secondary codes:** the 55 codes that appear in ≥ 5 train admissions become multi-hot columns. They cover 49% of secondary-code mentions.
- **Rare secondary codes:** the other 395 codes form a tail pool. Only their count per admission (`n_tail_codes`) is modeled. On decode, that many codes are drawn from the pool by train frequency, independently of the rest of the row. Individual rare codes stay realistic, but rare *combinations*, which are what re-identify a patient, are never reproduced.
- **`n_diagnoses`** is derived as the length of the decoded list, so the list and the count can't disagree.
- `--min-count` is a CLI flag, and sweeping it is the rare-code ablation for Phase 3.

### Output contract

This is what Track 2 and Track 4 can rely on. `generators/validate.py` enforces every item, and `generate.py` refuses to write a file that fails any of them.

1. Same columns, same order, and same dtype kinds as `output/mimic_demo_clean.csv`.
2. `split == "synthetic"` on every row.
3. `subject_id` counts up from 10,000,000 and `hadm_id` from 20,000,000. Neither collides with a real ID, and `hadm_id` is unique. Each synthetic patient has one admission.
4. Every categorical level and every ICD-9 code was seen in the **train** split. Anything else is either a holdout leak or an invented value.
5. Binary columns are in {0, 1}, `age` is in [0, 89], and rows with `age_89_plus` have `age == 89`.
6. Continuous columns are finite and non-negative, and `_abnormal_frac` is ≤ 1. NaN is allowed only in the three labs that have NaN in train, and a lab's `_mean` and `_abnormal_frac` are missing together.
7. `icd9_codes` is a JSON list of strings with no duplicates, its first element equals `icd9_primary`, and its length equals `n_diagnoses`.

Each run also writes `<generator>_seed<seed>.manifest.json` with the generator, hyperparameters, seed, row counts, SHA-256 of the training CSV, codec settings, and git commit. The same seed reproduces the CSV byte for byte.

### Statistical baseline (ADR-010)

A Gaussian copula over empirical marginals. Discrete columns map to frequency-sized slices of [0, 1], and continuous columns map by rank. With d > n the latent correlation matrix is singular, so it is shrunk toward the identity using the Ledoit-Wolf intensity (fitted value 0.668). `independent_marginals` is the same model with shrinkage fixed at 1, giving exact marginals and zero dependence. It's a reference floor, not one of the three benchmarked families.

### Self-tests

- **Round trip:** real train → encode → decode passes the contract, and every column comes back exactly except the resampled tail codes.
- **Negative tests:** the real holdout relabelled as synthetic fails on ID collisions, the holdout-only ethnicity from P-003, 18 unseen primary codes, and 30 rows of unseen codes. Deliberately corrupted rows fail on the exact invariant they break. Reading `icd9_primary` as int fails on 12 of 94 rows (P-005).
- **Determinism:** two runs with seed 42 give identical SHA-256.

Numbers are in [`baseline_generator_result.md`](baseline_generator_result.md).

### Diffusion generator design (Phase 2 build)

- **Basis:** TabDDPM (Kotelnikov et al., 2023). Numeric columns go through a quantile-normal transform fitted on train, then Gaussian diffusion. Every categorical and binary column, the 55 ICD-9 bits included, gets multinomial diffusion.
- **Denoiser:** an MLP with a sinusoidal timestep embedding over the concatenated noisy numerics and one-hot categoricals. With 94 rows it starts small, and depth, width and diffusion steps are the Phase 2 sweep.
- **Model selection without touching the holdout:** the holdout is reserved for Track 2 (ADR-001), so hyperparameters are chosen by k-fold within train, never by holdout score.
- **Memorization monitor:** distance to closest record (DCR), the privacy check TabDDPM itself reports. Within each fold, if synthetic rows sit much closer to the training folds than to the held-out fold, the model is copying rather than generalizing.
- **Rejected:** TabSyn-style latent diffusion. It needs a VAE trained first, which puts two models on 94 rows and doubles the overfitting surface.
- **Integration:** subclass `Generator` and register it in `generate.py`. The codec, contract and validator don't change.

### Literature review

| Work | What it contributes | Use in Doppel |
|---|---|---|
| Patki et al., 2016, *The Synthetic Data Vault*, IEEE DSAA | Gaussian copula synthesizer for tabular data | Statistical baseline design |
| Ledoit & Wolf, 2004, *A well-conditioned estimator for large-dimensional covariance matrices*, J. Multivariate Analysis | Shrinkage covariance for d ≈ n or d > n | Copula correlation at d = 110, n = 94 |
| Choi et al., 2017, *Generating Multi-label Discrete Patient Records using GANs* (medGAN), MLHC | Generation over multi-hot ICD-9 vectors | Precedent for the multi-hot code representation |
| Xu et al., 2019, *Modeling Tabular Data using Conditional GAN*, NeurIPS | CTGAN and TVAE | GAN/VAE arm, via SDV |
| Kotelnikov et al., 2023, *TabDDPM: Modelling Tabular Data with Diffusion Models*, ICML | Gaussian + multinomial diffusion for mixed-type tables, DCR privacy check | Design basis for the diffusion arm |
| Zhang et al., 2024, *Mixed-Type Tabular Data Synthesis with Score-based Diffusion in Latent Space* (TabSyn), ICLR | VAE latent space + score-based diffusion | Considered, rejected at n = 94 |
| Yuan et al., 2023, *EHRDiff: Exploring Realistic EHR Synthesis with Diffusion Models*, arXiv:2303.05656 | Diffusion over binary EHR code vectors | Precedent for diffusion on multi-hot codes |

Check each entry against the paper itself before it goes in the report.

---

## Commands

```bash
# 1. Setup (same pins as Track 2; the venv avoids clashing with a broken system scipy)
python3 -m venv .venv && source .venv/bin/activate
pip install pandas==2.3.3 numpy scikit-learn==1.8.0 scipy==1.17.1

# 2. Generate (writes output/synthetic/<generator>_seed<seed>.csv + .manifest.json)
python -m generators.generate --generator gaussian_copula --seed 42
python -m generators.generate --generator independent_marginals --seed 42

# 3. Check any synthetic CSV against the contract
python -m generators.validate output/synthetic/gaussian_copula_seed42.csv
```

Expected output: `PASS  wrote output/synthetic/gaussian_copula_seed42.csv and gaussian_copula_seed42.manifest.json`, then `PASS  output/synthetic/gaussian_copula_seed42.csv  (94 rows)`.

Synthetic output isn't committed because it regenerates from the seed in about a second (ADR-008).

---

## Key Decisions

**Why one shared codec instead of letting each generator preprocess its own way?** Otherwise a fidelity gap between two generators could come from how each one handled missing labs or rare codes, not from the model. One codec means one encoding, one set of constraints, and one decoder for all three. See ADR-008.

**Why model secondary ICD-9 codes at all, when Track 2's fidelity metrics currently skip `icd9_codes`?** The blueprint names rare, high-dimensional clinical codes as the hard case. Generating only the primary code would drop the project's stated difficulty. The multi-hot vocabulary gives the rare-code question a concrete knob (`min_count`). See ADR-009.

**Why `min_count = 5`?** Below about 5 admissions out of 94, a code's co-occurrence pattern is one patient's record, not a population pattern, so modeling it jointly is memorization by design. At 5 the vocabulary is 55 codes covering 49% of secondary mentions.

**Why is `n_diagnoses` derived instead of generated?** It's a deterministic function of the code list. Generating it separately lets a model produce a count that contradicts its own list.

**Why a Gaussian copula as the statistical baseline?** It's the standard statistical synthesizer (SDV's default), it handles mixed types through empirical marginals, and with Ledoit-Wolf shrinkage it stays well-defined at d > n where a plain covariance fit is singular. See ADR-010.

**Why does the validator only accept values seen in train?** Generators only ever see train (ADR-001). A category or code that exists only in the holdout can't legitimately appear in synthetic output, so this check doubles as a leakage tripwire. It fires on the Puerto Rican ethnicity category the moment holdout rows are passed off as synthetic.

**Why aren't synthetic outputs committed?** They regenerate from the seed in about a second, and committed copies go stale whenever the codec changes. Track 3's cleaned CSV is committed because regenerating it needs a manual PhysioNet download, which synthetic data doesn't.

**Why report every generator as mean ± sd over seeds?** On this holdout, one seed's TSTR AUROC has an SD of about 0.2 across seeds. Seed 42 of the independent-marginals floor, which has zero feature-label dependence, scored above the TRTR ceiling. See ADR-012.

---

## Outputs

| Output | Value |
|---|---|
| Generator package | `generators/` |
| Stage 2 contract | "Output contract" above, enforced by `generators/validate.py` |
| Modeling frame | 94 rows × 110 columns (55 ICD-9 multi-hot, 395-code tail pool) |
| Statistical baseline | `gaussian_copula`, Ledoit-Wolf shrinkage 0.668 |
| Reference floor | `independent_marginals` |
| Synthetic data | `output/synthetic/<generator>_seed<seed>.csv` + `.manifest.json` (regenerated, not committed) |
| Result writeup | [`baseline_generator_result.md`](baseline_generator_result.md) |
