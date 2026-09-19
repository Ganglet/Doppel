# Evaluation on Real Synthetic Data

**Phase:** Phase 2 — Core Development (blueprint Weeks 3–7), started 2026-09-19 on branch `track2-phase2-eval-runner`
**Owner:** Rayyan (Track 2 / Track B)
**Status:** In progress. The harness runs end to end on both Track 1 baselines over 20 seeds and writes the contract JSON Track 4 needs. The real comparison is blocked on CTGAN/TVAE and the diffusion model, and every result below has to be rerun when they land. Phase 1 is in [`B1_evaluation_pipeline.md`](B1_evaluation_pipeline.md).

---

## Objective

Move the Phase 1 metric code from a stand-in dataset to Track 1's real synthetic output, emit results in the shape Track 4's aggregation expects, and make the privacy numbers mean something. That last part had to be built because the first membership attack read "safe" for the wrong reason: it could not see the leak (P-010).

---

## What was built

### 1. Evaluation runner and contract JSON

```
output/synthetic/<generator>_seed<n>.csv   (Track 1, generated on demand if missing)
        |
   eval_runner.py  ---->  results/<generator>_seed<n>.json   (validated against
        |                          |                            contracts/schemas/evaluation_result.schema.json)
        |                  summarize_results.py, pareto.py
        |
mia_calibration.py, mia_direct_check.py  ---->  results/calibration/mia_calibration.json
```

`eval_runner.py` scores one synthetic CSV and validates the result against the schema before writing it. The schema forbids extra top-level keys, so everything sits under `metrics.fidelity`, `metrics.utility` and `metrics.privacy`. `results/` is gitignored and regenerated from the seed, like synthetic CSVs (ADR-014).

| Result JSON key | Meaning |
|---|---|
| `metrics.fidelity.mean_js_divergence` | mean JS divergence vs real train over 52 columns |
| `metrics.utility.tstr_auroc.<classifier>` | train-on-synthetic, test-on-real AUROC for `hospital_expire_flag` |
| `metrics.privacy.membership_inference`, `_gower`, `_codes` | shadow-model membership AUROC for the three realistic attacks |
| `metrics.privacy.membership_worst_case` | the highest of the three, with the winning attack named. This is the number to chart |
| `metrics.privacy.attribute_inference_targets` | member and non-member uplift and the member gap for `gender`, `first_careunit`, `age_bucket` |
| `metrics.privacy.attribute_inference` | the old ethnicity block, kept for continuity and not scored |

### 2. Seeds and summaries

Each generator is run over 20 seeds (42 to 61) and reported as mean ± sd (ADR-012). A run takes about 4 seconds because the shadow generators are cached and shared by the three membership attacks. `summarize_results.py` prints every headline metric as mean ± sd per generator.

### 3. Metric fixes and revised thresholds

Track 1 found that `fidelity_metrics.py` scored binary columns as JSD 0 whatever the positive rate, because 10-quantile binning collapses two values into one bin (P-007). Binary columns now use the categorical path and the report covers 52 columns. Two thresholds were dropped because they sit below the noise floor: absolute correlation cutoffs (real train vs holdout already scores 0.203) and "TSTR within 0.10 of TRTR" (seed sd is 0.15 to 0.22). See ADR-015 and [`eval_protocol.md`](../eval_protocol.md).

### 4. Membership inference made interpretable

| Piece | What it does |
|---|---|
| Three attacks in `membership_inference.py` | 4 numeric columns, Gower distance over all 53 features, Jaccard distance on ICD-9 code sets |
| `mia_calibration.py` | runs every attack against an exact-copy generator (ceiling 1.000), real rows the generator never saw (floor 0.49 to 0.50), and both baselines; also splits codes into once-seen and repeated as a diagnostic |
| `mia_direct_check.py` | attacks the real synthetic files without shadow models, with bootstrap intervals and a same-distribution half-train diagnostic |

The privacy score is the strongest realistic attack (ADR-016). The 4-column attack read 0.51 to 0.52 for both baselines while the code-set attack reads 0.64, and the leak sits in codes seen once in train (0.84 vs 0.62 for repeated codes). The direct check on the real target is consistent with the shadow numbers but its intervals are too wide to confirm them (P-010, P-012).

### 5. Attribute inference on attributes both splits cover

The ethnicity target was unusable because one class is missing from train (P-003). The attacker now predicts `gender`, `first_careunit` and an age bucket, is scored on members and non-members separately with balanced accuracy minus chance, and the member gap is the privacy number (ADR-017). An exact-copy attacker gives gaps of 0.57 to 0.77. Neither baseline shows a gap beyond the no-dependence control, and the attack is only sensitive to memorization on a dataset this small (P-011).

### 6. Pareto frontier

`pareto.py` reduces each generator to fidelity (JS, lower), utility (mean TSTR AUROC, higher) and privacy (`membership_worst_case`, lower), marks non-dominated generators, and bootstraps frontier membership and pairwise dominance over seeds (ADR-018). On the two baselines neither dominates the other.

### 7. Reproducibility across machines

Copula seed-42 output changes with the numpy build, and TSTR moves from 0.931 to 0.770 (logistic regression) between numpy 2.4.6 and 2.2.6. The likely cause is the copula's `method="eigh"` sampler; `method="cholesky"` gave 0 differing cells across the two versions on a scratch copy. The fix belongs to Track 1 and is proposed but not applied (P-008, P-009). `requirements.txt` pins the versions this work was run with.

### Not done

- CTGAN/TVAE and the diffusion model are not evaluated because they don't exist yet. The two generators here are the statistical baseline and a no-dependence control.
- No Pareto plot. A plot of two near-identical points says nothing, so it waits for real generators.
- The direct attack on a generator fit on all 94 rows has no valid non-members, so its magnitude is unmeasured.
- The five gaps the [survey](membership_inference_survey.md) found against the literature: true-positive rate at low false-positive rate, a per-record vulnerability report, a density-based attack, a release-only attacker, and the "nothing found is not safe" wording. None is implemented.

---

## Commands

```bash
# Setup
pip install -r requirements.txt

# Score both baselines over 20 seeds (generates output/synthetic/*.csv if missing)
for g in gaussian_copula independent_marginals; do
  for s in $(seq 42 61); do python eval_runner.py --generator $g --seed $s; done
done

# Verify: 40 result files, then mean +/- sd and the Pareto frontier
ls results/*.json | wc -l
python summarize_results.py
python pareto.py

# Membership attack controls and the direct check
python mia_calibration.py
python mia_direct_check.py

# Attribute inference, including the exact-copy ceiling control
python attribute_inference.py
```

Expected: `40`, then two generators with `n_seeds=20`, then both generators on the frontier with dominance probabilities of 0.01 and 0.00.

---

## Key Decisions

**Why is fidelity measured against train, not the holdout?** Train is what the generator was fit on, so it answers "does the model reproduce its training distribution". Real train vs holdout is only the sampling-noise floor (mean JS 0.099, correlation 0.203). See ADR-014.

**Why 20 seeds and mean ± sd everywhere?** One seed of a signal-free generator scored above the real-data ceiling on TSTR, because the holdout has 6 positives among 35 rows. See ADR-012.

**Why is the privacy score the strongest attack, not the original one?** A score near 0.5 says the attack found nothing, which is a claim about the attack until it has found something on a generator that leaks. The ceiling and floor arms are what give it meaning. See ADR-016 and P-010.

**Why report a member gap instead of attacker accuracy for attribute inference?** Uplift on unseen rows is ordinary statistical inference, not a privacy leak. Only the extra accuracy on training records is specific to membership. See ADR-017.

**Why are correlation and utility not pass/fail?** Both thresholds sat below the noise floor, so the seed would have decided the outcome. They are reported against references instead. See ADR-015.

**Why is the copula's sampler not fixed here?** `generators/` is Track 1's code and the change alters every copula sample, so his published seed-level numbers would need regenerating. It is proposed with evidence in P-009.

---

## Outputs

| Output | Value |
|---|---|
| Runner and summaries | `eval_runner.py`, `summarize_results.py` |
| Membership controls | `mia_calibration.py`, `mia_direct_check.py`, output in `results/calibration/mia_calibration.json` |
| Attribute inference | `attribute_inference.py` (`run_attribute_targets`) |
| Pareto frontier | `pareto.py` |
| Pinned dependencies | `requirements.txt` (pandas 2.3.3, numpy 2.4.6, scikit-learn 1.8.0, scipy 1.17.1, jsonschema 4.26.0) |
| Result files | `results/<generator>_seed<n>.json`, 40 files (gitignored) |
| Baseline evaluation | [`baseline_evaluation_result.md`](baseline_evaluation_result.md): fidelity and utility cannot separate the baselines |
| Membership calibration | [`membership_calibration_result.md`](membership_calibration_result.md): both baselines at 0.64 on ICD-9 code sets, floor 0.49 |
| Attribute inference | [`attribute_targets_result.md`](attribute_targets_result.md): no member gap beyond the control |
| Pareto frontier | [`pareto_result.md`](pareto_result.md): neither baseline dominates |
| Literature survey | [`membership_inference_survey.md`](membership_inference_survey.md): 18 sources checked against their arXiv, PoPETs or PMC pages |
| Log entries | ADR-012, ADR-014 to ADR-018 and P-007 to P-012 in [`problems_and_decisions.md`](problems_and_decisions.md) |
| Rerun needed | when CTGAN/TVAE and the diffusion model exist |
