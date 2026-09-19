# Utility Pipeline Result — TRTR/TSTR harness runs and produces AUROC scores (2026-09-17)

Raw evidence that `evaluation/utility_eval.py`'s train-on-real/test-on-real (TRTR) and train-on-synthetic/test-on-real (TSTR) pipeline works end-to-end. Reproduce with `python -m evaluation.utility_eval` from the repo root.

> **Stand-in run (Phase 1).** This measured real train against real holdout, not a generator. The same metric on real synthetic data is in [`baseline_evaluation_result.md`](baseline_evaluation_result.md) and [`B2_eval_runner.md`](B2_eval_runner.md).


---

## Method (honest framing)

TRTR is real: 5-fold stratified cross-validation on the real `train` split, evaluating both classifiers on real held-out folds. TSTR is **not real** in this run — the real `train` split stands in for synthetic data (no generator exists yet), evaluated against the real `holdout` split. This run validates the pipeline's mechanics (feature encoding, median imputation, standardization, AUROC scoring, the TRTR/TSTR gap calculation) — it does not validate that any generator preserves downstream-utility signal.

The gap direction found here (Random Forest's "TSTR" beating its own TRTR baseline, −0.1478) is specifically a red flag *for this framing*, not a positive result: it's what happens when "synthetic" data is actually just the real training distribution scored against a small, non-independent holdout, not evidence a generator works well. **Honest phrasing for the report: "the utility evaluation pipeline is implemented and validated on real data; TSTR numbers against actual synthetic data have not yet been measured."**

---

## Results

| Classifier | TRTR AUROC (5-fold CV, real train) | TSTR AUROC (stand-in "synthetic" -> real holdout) | Gap (TRTR − TSTR) |
|---|---|---|---|
| Logistic Regression | 0.5778 | 0.4885 | 0.0893 |
| Random Forest | 0.7373 | 0.8851 | −0.1478 |

Target: `hospital_expire_flag` (see [`B1_evaluation_pipeline.md`](B1_evaluation_pipeline.md) for why this label was chosen over `readmit_30d`).

---

## Raw evidence

```
$ python -m evaluation.utility_eval
TRTR baseline (5-fold CV on real train):
  logistic_regression: 0.5778
  random_forest: 0.7373

TSTR (train on stand-in synthetic, test on real holdout):
  logistic_regression: 0.4885
  random_forest: 0.8851

Gap (TRTR - TSTR):
  logistic_regression: 0.0893
  random_forest: -0.1478
```

---

## Contrast with the first run attempt

An earlier run of this pipeline crashed with `NotFittedError: This SimpleImputer instance is not fitted yet` (see [`problems_and_decisions.md`](problems_and_decisions.md) P-001), and the version before the fix logged `ConvergenceWarning: lbfgs failed to converge` on every fold (P-002). Both are fixed in the numbers above — the imputer/encoder/scaler are now correctly threaded through every fold, and numeric features are standardized before logistic regression.
