# Full Evaluation and Pareto Validation

**Phase:** Phase 3 — Integration & Evaluation (blueprint Weeks 8–11), on branch `track2-phase3-full-evaluation`
**Owner:** Rayyan (Track 2 / Track B)
**Status:** Done for the generators that exist: the statistical baseline (two configs), CTGAN, TVAE and the independent-marginals floor, 20 seeds each. The diffusion model does not exist yet, and the neural configs are Track 1's untuned carry-overs, so this has to be rerun when either changes. Phase 2 is in [`B2_eval_runner.md`](B2_eval_runner.md).

---

## Objective

Run the whole evaluation harness on every generator family Track 1 has built, finish the privacy suite so its scores can be trusted, and compute and validate the fidelity, utility and privacy frontier. The privacy attacks had never been shown to detect a generator that actually leaks, so this phase added one that verifiably does (TVAE) and used it to check them.

---

## What was built

### 1. Named arms and an honest data path

`evaluation/arms.py` defines each evaluated configuration as a generator plus hyperparameters, and `--generator` takes an arm name (ADR-025). Three things changed in how the runner gets data:

| Change | Why |
|---|---|
| Synthetic data is regenerated on every run into `output/synthetic/eval/<arm>/` | A reused CSV from older generator code silently mixed old and new draws (P-015) |
| Shadow generators are fitted with Track 1's `synthesize` and cached on disk, keyed by a hash of `generators/`, the dataset, the hyperparameters, the seed and the member rows | Calibration and the direct check reuse the runner's fits instead of refitting CTGAN, and a code change invalidates them |
| Synthetic CSVs are read through `generators.schema.load_real` | A plain `pd.read_csv` dropped the leading zero of `icd9_primary` and distorted fidelity for every Phase 2 result (P-014) |

### 2. Membership suite completed

| Piece | What it does |
|---|---|
| Pooled TPR at 5% and 1% FPR | Reported for every membership attack next to AUROC, from the pooled held-out predictions of all shadow worlds (ADR-026) |
| `mia_calibration` on seven arms | Ceiling (exact copy), floor (unseen real rows), the five evaluated arms, five attacks each, run in parallel over (arm, seed) |
| Per-record report | Each record's attack advantage against its number of once-seen ICD-9 codes |
| `mia_direct_check` on five arms | Direct attack on the real synthetic files with bootstrap intervals and a same-distribution half-train diagnostic |
| `mia_count_check` | Tests whether a neighbourhood-count feature strengthens the attack. It does not |
| `synthetic_coverage` | Counts how many distinct training rows each generator's output sits nearest to |

The positive control works: TVAE ranks most leaky on the Gower, code-set and worst-case attacks and the 4-column attack cannot see it. Every generator leaks through once-seen codes, and TVAE additionally leaks through ordinary rows because it collapses onto about a third of the training rows. See [`positive_control_result.md`](positive_control_result.md).

### 3. Full evaluation

Five arms over 20 seeds, 100 runs, in a separate venv built from Track 1's neural pins (torch 2.14.0, ctgan 0.12.1, rdt 1.22.0) so the global Python was not changed. TVAE reaches the real-data utility ceiling by copying, CTGAN learns no dependence, and the 0.25-shrinkage copula matches TVAE's utility with much better fidelity and less leakage. See [`full_evaluation_result.md`](full_evaluation_result.md).

### 4. Pareto validation

`evaluation.pareto` now recomputes the frontier under eight axis sets and prints the privacy ordering per attack (ADR-027). All five arms are non-dominated, TVAE's place depends only on utility, and a weak privacy axis would rank TVAE safest. See [`full_pareto_result.md`](full_pareto_result.md).

### 5. Reproducibility

TVAE and CTGAN seed 42 are byte-identical under torch 2.12.0 and torch 2.14.0 on this machine. The copula reproduces across numpy builds since Track 1's Cholesky fix (P-013). Other machines are untested.

### Not done

- **The diffusion model** is not evaluated because it does not exist yet.
- **The neural configs are untuned.** Track 1's next sweep tests smaller networks and stronger regularisation, so CTGAN and TVAE numbers may move.
- **Two survey gaps remain:** a density-based attack, and a release-only attacker.
- **No Pareto plot** and no update to the README's Track 2 sections.
- **Track 4 has not wired these results in.** The dashboard still reads only generator manifests.
- **The direct attack on the real target is inconclusive** because no valid non-members exist for a generator fitted on all 94 rows.

---

## Commands

```bash
# Setup (neural extras: torch 2.14.0, ctgan 0.12.1, rdt 1.22.0; ctgan and rdt are BUSL-1.1)
pip install -r generators/requirements-neural.txt

# Evaluate every arm over 20 seeds. CTGAN is slow (about 4.5 minutes of fitting per seed on this laptop
# by solo timings, and 8.5x slower per fit with six running at once), so use six workers or fewer.
for arm in independent_marginals gaussian_copula gaussian_copula_shrink025 ctgan tvae; do
  for s in $(seq 42 61); do python -m evaluation.eval_runner --generator $arm --seed $s; done
done

# Verify: 100 result files, then mean +/- sd per arm and the frontier with its sensitivity table
ls results/*.json | wc -l
python -m evaluation.summarize_results
python -m evaluation.pareto

# Membership controls (they reuse the runner's cached shadow fits), direct check, diagnostics
python -m evaluation.mia_calibration --workers 6
python -m evaluation.mia_direct_check --workers 6
python -m evaluation.mia_count_check
python -m evaluation.synthetic_coverage
```

Expected: `100`, five arms with `n_seeds=20`, all five arms on the frontier, and TVAE highest on the worst-case membership score (0.680).

---

## Key Decisions

**Why these five arms?** Track 1 carried the 0.25-shrinkage copula and 300-epoch CTGAN into Phase 3 and proposed TVAE as a positive control (ADR-024), and the independent floor and Ledoit-Wolf copula are the Phase 1 baselines. See ADR-025.

**Why include TVAE when it fails Track 1's memorization guard?** Because it does memorize, which makes it the one real generator on which a privacy attack can be checked. An attack that rates it safe cannot be trusted on the others, and the 4-column attack does exactly that.

**Why regenerate data on every run and key the shadow cache by content?** Reuse by filename mixed old and new generator code once already. See P-015.

**Why is the Pareto privacy axis still worst-case AUROC and not the low-FPR true-positive rate?** The 1% figure rests on about 376 pooled non-members and has a seed sd of about 0.02. See ADR-026.

**Why report the frontier with a sensitivity table?** Five non-dominated arms read alone look like five wins, and the sensitivity table shows which arms owe their place to one axis. See ADR-027.

**Why a separate venv?** It reproduces Track 1's pins exactly without changing the global Python packages on this machine.

---

## Outputs

| Output | Value |
|---|---|
| Arms registry | `evaluation/arms.py` |
| Membership and diagnostics scripts | `evaluation/mia_calibration.py`, `evaluation/mia_direct_check.py`, `evaluation/mia_count_check.py`, `evaluation/synthetic_coverage.py` |
| Pareto validation | `evaluation/pareto.py` (sensitivity and privacy ordering) |
| Result files | `results/<arm>_seed<n>.json`, 100 files, and `results/calibration/mia_calibration.json` (gitignored, regenerated) |
| Full evaluation | [`full_evaluation_result.md`](full_evaluation_result.md): TVAE at the utility ceiling by copying, CTGAN learns nothing |
| Positive control | [`positive_control_result.md`](positive_control_result.md): TVAE detected, every generator leaks once-seen codes |
| Pareto | [`full_pareto_result.md`](full_pareto_result.md): all five arms non-dominated |
| Log entries | ADR-025 to ADR-027 and P-014 to P-016 in [`problems_and_decisions.md`](problems_and_decisions.md) |
| Rerun needed | when the diffusion model or a retuned neural config lands |
