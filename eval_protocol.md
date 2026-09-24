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
random guessing). AUROC ≥ 0.65 = fail (meaningful membership leakage). Between 0.55 and 0.65 = review, not
pass or fail.

**Revision (2026-09-19):** the attack is now run three ways, and the **strongest realistic attack is the
privacy score**: nearest-neighbour distance on 4 numeric columns (`numeric4`), Gower distance over all 53
features (`gower`), and Jaccard distance on ICD-9 code sets (`icd9_codes`). The 4-column attack alone read
0.51 to 0.52 for both baselines while the code-set attack reads 0.64, so it cannot be the only attack.
Every run is read against two calibration anchors from `evaluation/mia_calibration.py`: an exact-copy generator
(ceiling, 1.000) and real rows the generator never saw (floor, 0.49 to 0.50, seed sd about 0.03). Two
diagnostic attacks (`codes_once`, `codes_repeated`) use train code frequencies an attacker would not have,
so they locate a leak but are not scored. See
[`docs/membership_calibration_result.md`](docs/membership_calibration_result.md).

**Literature basis:** [`docs/membership_inference_survey.md`](docs/membership_inference_survey.md) places these attacks
in the distance-to-closest-record family used by the SynthEHRella and Nature Communications EHR benchmarks and
lists five gaps against the literature (no true-positive rate at low false-positive rate, no per-record report,
no density-based attack, a stronger attacker than release-only, and wording: an AUROC near 0.5 means the attacks
found nothing, not that the data is safe).

### Attribute inference (implemented, `evaluation/attribute_inference.py`)
An attacker trained on the synthetic data predicts a withheld attribute from every other column. It is
scored on the real train rows (members) and the real holdout rows (non-members) separately, as balanced
accuracy minus chance, and the **member gap** (member uplift minus non-member uplift) is the
privacy-relevant number, because uplift on unseen rows is ordinary statistical inference. Targets are
`gender`, `first_careunit` and an age bucket (<65, 65-79, 80+), the attributes with class coverage in both
splits. The exact-copy control (member gaps 0.57 to 0.77) is the ceiling; `independent_marginals` is the
no-dependence arm each generator's gap is read against. No pass/fail threshold is set: real data supports
so little inference here that a threshold would be decided by noise. See
[`docs/attribute_targets_result.md`](docs/attribute_targets_result.md).

**Superseded (2026-09-19):** the earlier version targeted `ethnicity` and scored holdout rows only. On the
current split `HISPANIC/LATINO - PUERTO RICAN` is 15 of 35 holdout admissions and 0 of 94 train admissions,
so the attacker never saw that class and predicted the majority class every time (P-003). That run is kept
in the repo (`run_attribute_inference`) and in the results JSON as `attribute_inference`, but it is not
scored.

## 5. Interface contract

- Input: any generator's synthetic CSV must match the column schema of `output/mimic_demo_clean.csv`
  (same columns Track 1 trains against, per Anoushka's `schema_and_feature_dictionary.md` §8).
- Until Track 1 delivers real synthetic data, this protocol is built and self-tested by using the
  real `train` split as a synthetic-data stand-in against the real `holdout` split — same code path,
  swapped input once real generator output exists.
- Each metric module lives standalone (`evaluation/fidelity_metrics.py`, `evaluation/utility_eval.py`,
  `evaluation/membership_inference.py`) and can be run independently or imported by the aggregation stage
  (Track 4).

**Result JSON keys Track 4 should read (2026-09-19):** `metrics.fidelity.mean_js_divergence`,
`metrics.utility.tstr_auroc.<classifier>`, and `metrics.privacy.membership_worst_case.mean_attack_auroc`
(the highest mean AUROC over `membership_inference`, `membership_inference_gower` and
`membership_inference_codes`, with the winning attack named in `.attack`). Do not chart
`membership_inference` alone: it reads 0.50 to 0.52 for every arm while the worst case reads 0.64 to 0.68. Each membership block also carries `tpr_at_fpr_5pct` and `tpr_at_fpr_1pct`.
The old ethnicity `attribute_inference` block is not scored.

## 6. Pareto frontier

`evaluation/pareto.py` reduces each arm to fidelity (mean JS vs train, lower is better), utility (mean TSTR
AUROC over the two classifiers, higher is better) and privacy (worst-case membership AUROC, lower is
better), marks arms no other arm dominates, and bootstraps frontier membership and pairwise dominance over
seeds. **Validation (Phase 3):** the frontier is recomputed under eight axis choices (a correlation axis, one
classifier, one attack at a time, no utility axis), and the privacy axis is checked against the TVAE positive
control. See [`docs/full_pareto_result.md`](docs/full_pareto_result.md). On the current five arms every arm is
non-dominated, so the frontier shows trade-off directions and does not rank generators. It must be rerun
when the diffusion model or a retuned generator arrives.

## 7. Generator arms and the positive control (Phase 3)

Arms are defined in `evaluation/arms.py` as a generator plus hyperparameters, and `--generator` takes an arm
name. The five arms are `independent_marginals` (floor), `gaussian_copula` (Ledoit-Wolf), `gaussian_copula_shrink025`
(the config Track 1 carried into Phase 3), `ctgan` (300 epochs) and `tvae` (300 epochs). **TVAE is the membership
and attribute attack's positive control:** Track 1's sweep found it copies 52 to 71% of its rows, so an
attack that rates it as safe is too weak to trust. On the current run the Gower, ICD-9 and worst-case
membership attacks and the attribute member gap all rate it most leaky, and the 4-column attack rates it least
leaky, which is why the 4-column attack is not the privacy score.

Reporting added in Phase 3: pooled true-positive rate at 5% and 1% false-positive rate for every membership
attack (chance 0.05 and 0.01; closes survey gap 1), and a per-record advantage report in
`evaluation.mia_calibration` (closes survey gap 2). Two survey gaps stay open: a density-based attack, and a
release-only attacker.

Operational rules:

- The runner always regenerates the synthetic data for an arm and seed, and shadow-generator fits are cached on
  disk under `output/synthetic/shadow_cache/` by a key that includes the `generators/` source, so results
  cannot silently mix old and new generator code (P-015).
- Neural arms need `generators/requirements-neural.txt` (torch 2.14.0, ctgan 0.12.1, rdt 1.22.0). `ctgan` and
  `rdt` are BUSL-1.1, source-available and non-production, not OSI open source.
- Run neural arms with about six workers or fewer. CTGAN is 8.5× slower per fit with six running at once (P-016).
