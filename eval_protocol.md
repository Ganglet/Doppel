# Doppel — Evaluation Protocol
**Track 2 · Privacy & Utility Evaluation · Phase 1 deliverable**

## 1. Downstream utility task

**Chosen label: `hospital_expire_flag`** (in-hospital mortality).

Checked class balance on Anoushka's `output/mimic_demo_clean.csv` before deciding:

| Label | Train pos/neg | Holdout pos/neg |
|---|---|---|
| `hospital_expire_flag` | 34 / 60 | 6 / 29 |
| `readmit_30d` | 9 / 85 | 2 / 33 |

`readmit_30d` has only 2 positive cases in the entire holdout set — any AUROC computed on that is
noise on a 100-patient demo. `hospital_expire_flag` has 6 holdout positives and a 31% overall positive
rate, which is workable. `readmit_30d` stays available as a secondary/stretch label if time allows.

## 2. Fidelity metrics

Run column-by-column, synthetic vs. the real **train** split (the data the generator was fit on), on the
same feature set (excluding `subject_id`, `hadm_id`, `icd9_codes`, `split`). Real train vs. real holdout is
reported alongside as the sampling-noise floor, not as a generator score.

| Metric | Applies to | Formula | Threshold |
|---|---|---|---|
| Jensen–Shannon divergence | categorical, binary, and binned continuous | JSD(P\|\|Q) over the column's value distribution, base-2 (range 0–1) | mean JSD ≤ 0.10 = good, ≤ 0.20 = acceptable, > 0.20 = fail |
| Pairwise correlation preservation | numeric columns | mean absolute difference between real and synthetic Pearson correlation matrices (upper triangle only) | reported against two references, not gated: the real-vs-real floor (0.203) and the `independent_marginals` baseline (0.163) |
| Dimension-wise distribution check | numeric columns | two-sample Kolmogorov–Smirnov test per column | fraction of columns with KS p ≥ 0.05 reported as a summary stat, not a hard gate |

Continuous columns are binned into 10 quantile-based bins before computing JSD. Binary columns
(`hospital_expire_flag`, `readmit_30d`, `age_89_plus`) go through the categorical path, because 10-quantile
binning collapses two values into one bin and scores JSD 0 regardless of the positive rate (P-007).

**Revision (2026-09-19):** the original absolute correlation thresholds (≤ 0.10 good, ≤ 0.20 acceptable)
were dropped. Real train vs. real holdout already scores 0.203, so no generator could pass against the
holdout, and a 94-row sample carries roughly 1/√94 ≈ 0.10 of sampling noise per correlation entry.

## 3. Downstream utility metric

**Protocol:** train-on-synthetic, test-on-real (TSTR), compared against train-on-real, test-on-real
(TRTR) as the reference ceiling.

- Target: `hospital_expire_flag`
- Classifiers: Logistic Regression (baseline) and Random Forest
- Metric: AUROC (chosen over accuracy because of the ~31%/69% class split)
- TRTR baseline: 5-fold stratified CV on the real train split
- TSTR: train on the generator's synthetic data, evaluate on the real holdout split
- **Seeds:** every generator is run over 20 seeds (42–61) and reported as mean ± sd (ADR-012). A single
  seed is never reported.
- **Comparison:** the reference points are the `independent_marginals` mean (zero feature-label dependence
  by construction, so the chance floor) and the TRTR ceiling. Generators are compared with a Welch t-test
  over seeds, uncorrected for multiple comparisons.

**Revision (2026-09-19):** the original threshold ("TSTR within 0.10 of TRTR = good") was dropped. The
seed-to-seed sd of TSTR AUROC is 0.15–0.22 on this holdout (6 positives in 35 rows), which is larger
than the threshold, so pass/fail would be decided by the seed. Utility is reported descriptively until a
larger holdout exists.

## 4. Privacy metrics

### Membership inference (primary)
Shadow-model attack (Shokri et al. style):
1. Train N shadow models on random resampled subsets of the population pool, each with a known
   member/non-member split.
2. For each shadow model, record its output confidence on both member and non-member records —
   this becomes the attack model's training data.
3. Train a binary attack classifier (member vs. non-member) on those confidence vectors.
4. Evaluate the attack's AUROC against the real target generator/classifier.

**Threshold:** attack AUROC within 0.05 of 0.50 (i.e. 0.45–0.55) = good privacy (attacker is close to
random guessing). AUROC ≥ 0.65 = fail (meaningful membership leakage).

### Attribute inference (implemented — `attribute_inference.py`)
Given a partial record (subset of known attributes), attempt to reconstruct a withheld sensitive
attribute (`ethnicity`) better than the population base rate. Reported as attacker accuracy uplift
over the base-rate guess (always predicting the majority class); no hard pass/fail threshold set yet.

**Known data caveat found while testing:** on the current train/holdout split, `HISPANIC/LATINO -
PUERTO RICAN` accounts for 15/35 (43%) of the holdout set but 0/94 of the train set — the
patient-level 80/20 split happened to put every patient of that ethnicity into holdout. This isn't a
bug in the attack code; it means the attacker (and any model trained on `train`) has literally never
seen that class, so the current uplift reading of 0.0 reflects the split's small-sample gap for this
feature, not the generator's actual privacy behavior. Flagged to Track 3 — worth a second look once
real synthetic data is available, since the same gap will affect Track 1's generator training too.

## 5. Interface contract

- Input: any generator's synthetic CSV must match the column schema of `output/mimic_demo_clean.csv`
  (same columns Track 1 trains against, per Anoushka's `schema_and_feature_dictionary.md` §8).
- Until Track 1 delivers real synthetic data, this protocol is built and self-tested by using the
  real `train` split as a synthetic-data stand-in against the real `holdout` split — same code path,
  swapped input once real generator output exists.
- Each metric module lives standalone (`fidelity_metrics.py`, `utility_eval.py`,
  `membership_inference.py`) and can be run independently or imported by the aggregation stage
  (Track 4).
