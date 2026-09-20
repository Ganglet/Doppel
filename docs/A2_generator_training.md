# Generator Training & Model Selection

**Phase:** Phase 2 — Core Development (Weeks 3–7)
**Owner:** Angshuman (Track 1 / Track A)
**Status:** CTGAN and TVAE are on the shared interface. The in-train model-selection harness (patient folds, DCR memorization, fidelity) is built and calibrated. The initial sweep of 165 fits is done. At this n the Gaussian copula leads, CTGAN underfits (below the independent floor), and TVAE memorizes (52–71% near-copies). The output contract is reconciled with Track 4. The diffusion generator is my Phase 2 build, and its brief is below. See [`problems_and_decisions.md`](problems_and_decisions.md) ADR-020 to ADR-024 and [`sweep_result.md`](sweep_result.md).

---

## Objective

Get the GAN-family generators onto the Phase 1 interface, and build what every later tuning decision depends on: a way to compare hyperparameters on 94 rows without touching the holdout and without rewarding memorization. On a training set this small, the most flexible model can post the best in-sample fidelity by copying its training rows, so a sweep scored on fidelity alone would pick exactly the wrong model.

---

## What was built

### CTGAN and TVAE (ADR-020)

```
generators/ctgan_tvae.py    CTGAN, TVAE: ctgan v0.12.1 on the shared modeling frame, CPU, 1 torch thread
generators/generate.py      lazy registry (torch loads only for neural generators), --param key=value
```

Both pass the Stage 2 contract and reproduce byte for byte from the seed. On 94 rows one epoch is one gradient step, so `epochs` is the step count. That's the dimension the sweep varies.

### Model selection inside train (ADR-021)

```
generators/diagnostics.py   patient_folds, Gower nearest-record distance, DCR ratio + near-copy rate
generators/sweep.py         (generator x config x seed x fold) tasks in parallel processes, mean +- sd per config
```

Train is split into 5 patient-level folds. For each fold, the generator fits on 4/5 of train and is scored two ways:

- **Fidelity to the rows it fit**, using Track 2's `run_fidelity_report` unchanged (mean JSD, correlation difference).
- **Memorization against the unseen fifth.** `dcr_ratio` is the median distance from synthetic rows to the fit rows, divided by the same for real unseen rows. `near_copy_rate` is the share of synthetic rows closer to the fit rows than the nearest 5% of real unseen rows.

The holdout is never read. The diagnostic was calibrated before any generator was scored with it:

| Input scored as "synthetic" | `dcr_ratio` | `near_copy_rate` | Meaning |
|---|---|---|---|
| Real unseen rows | 1.000 | 0.059 | reference point: as novel as real data |
| Exact copies of the fit rows | 0.000 | 1.000 | pure memorization |

### Contract reconciliation with Track 4 (ADR-022)

Every manifest failed Track 4's draft `generator_output.schema.json`: `gaussian_copula` wasn't an allowed name, and the strict schema rejected the seed and training-data hash. Manifests now carry all of Track 4's required fields, and the schema is amended to declare the reproducibility fields, with `seed` required. All four generators' manifests validate, and a manifest missing its seed still fails. The review is recorded in [`contracts/README.md`](../contracts/README.md) §5.

### Dependencies and cross-environment reproducibility (ADR-023, P-013)

Track 1 runs on the team's root `requirements.txt`, the environment Track 4's `python:3.11-slim` image installs. `generators/requirements-neural.txt` adds torch, ctgan and rdt on top of it. Track 2 found that the copula's seed-42 file changed between numpy builds (P-008, P-009). The cause was `eigh` sampling from a matrix with 17 identical eigenvalues, which is forced by d > n, so the copula now samples through Cholesky. All four generators at seed 42 are byte-identical on Python 3.11.5 / numpy 2.4.6 and on Python 3.12 / numpy 2.5.3.

### Diffusion generator: build brief

The design is in [`A1_generative_modeling.md`](A1_generative_modeling.md). It's done when:

1. `generators/diffusion.py` defines `TabularDiffusion(Generator)` with `name = "tabular_diffusion"`, registered as `"tabular_diffusion": "diffusion:TabularDiffusion"` in `generate.GENERATORS` and added to `sweep.GRID`.
2. `python -m generators.generate --generator tabular_diffusion --seed 42` prints `PASS`. The codec and validator are unchanged.
3. The same seed gives the same SHA-256, twice on one machine and across two numpy builds (P-013). Seed torch from `rng.integers(2**31)` and set `torch.set_num_threads(1)`, as in `ctgan_tvae.py`. Avoid anything whose result isn't unique, such as eigendecompositions of matrices with repeated eigenvalues.
4. Across the sweep's folds and seeds, at least one config beats the carried-forward copula (λ = 0.25, correlation difference 0.119, ADR-024) while keeping `dcr_ratio ≥ 0.95` and `near_copy_rate ≤ 0.10`. If none does, that's a reportable result, not a failure. Both neural baselines already missed this bar in opposite directions. Watch for TVAE's failure mode in particular: a diffusion model on 75 rows can collapse onto a subset of patients too.

---

## Commands

```bash
# 1. Setup (Python 3.11, same as the Docker image; the neural file includes the root requirements.txt)
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r generators/requirements-neural.txt

# 2. Generate one synthetic dataset (any registered generator)
python -m generators.generate --generator ctgan --seed 42 --param epochs=1000
python -m generators.validate output/synthetic/ctgan_seed42.csv

# 3. Sweep (all generators, 3 seeds, 5 patient folds; writes output/sweeps/)
python -m generators.sweep --seeds 0 1 2
python -m generators.sweep --only ctgan --seeds 0 1 2 --workers 6
```

---

## Key Decisions

**Why wrap `ctgan` directly instead of SDV?** SDV's synthesizers re-detect types and apply their own transforms on top of the shared codec, which would undo ADR-008. See ADR-020.

**Why one torch thread?** Profiled: one thread is 1.5–2.2× faster than eight on these matrices, and a fixed thread count keeps results identical across machines. Parallelism goes across processes instead: one per fold and seed in the sweep, and one per Job in Track 4's pipeline.

**Why not tune on the holdout, or on fidelity alone?** The holdout is Track 2's test set (ADR-001). Fidelity to the training rows is maximized by copying them. DCR against unseen real rows is the only in-train signal that separates learning from copying. See ADR-021.

**Why Gower distance?** The modeling frame mixes 44 numeric columns with 66 discrete ones. Gower weights every column equally and needs no arbitrary scaling between one-hot and continuous features.

**Why carry CTGAN forward if it's below the floor?** It's one of the blueprint's three families, and "a GAN underfits at n = 94" is a result the benchmark should show, not hide. Its least-bad setting (300 epochs) goes to Phase 3, and the next sweep checks whether smaller networks close the gap. See ADR-024.

**Why is TVAE useful even though it fails the guard?** It's a real generator that verifiably memorizes, which makes it the positive control Track 2's membership-inference attack needs. An attack that rates TVAE as safe can't be trusted on anything else.

**Why amend Track 4's schema rather than drop the extra manifest fields?** Without the seed and training-data hash, a result can't be traced to the run that produced it. That traceability is the project's stated contribution. See ADR-022.

---

## Outputs

| Output | Value |
|---|---|
| GAN-family generators | `ctgan`, `tvae` in `generators/ctgan_tvae.py` |
| Model-selection harness | `generators/diagnostics.py`, `generators/sweep.py` |
| Amended contract | `contracts/schemas/generator_output.schema.json` |
| Dependencies | root `requirements.txt` (team pins) + `generators/requirements-neural.txt` |
| Cross-environment check | all four generators byte-identical on Python 3.11 / numpy 2.4.6 and Python 3.12 / numpy 2.5.3 (P-013) |
| Sweep output | `output/sweeps/sweep_<utc>.csv` + `_summary.csv` (regenerated, not committed) |
| Result writeup | [`sweep_result.md`](sweep_result.md) |
