# Baseline Evaluation Result — Track 2 scores Track 1's two baselines over 20 seeds (2026-09-19)

Raw evidence for the first evaluation of real synthetic data through the full Track 2 harness. Reproduce with `python eval_runner.py --generator <name> --seed <n>` for each seed, then `python summarize_results.py`. Each run writes `results/<generator>_seed<n>.json`, which validates against [`contracts/schemas/evaluation_result.schema.json`](../contracts/schemas/evaluation_result.schema.json).

---

## Method (honest framing)

Both generators (`gaussian_copula`, `independent_marginals`) were fit on the 94 train rows and run over 20 seeds (42 to 61), 40 runs in total, as ADR-012 requires. Fidelity compares each synthetic set to real train. Utility trains on the synthetic set and tests on the 35-row real holdout. Attribute inference trains on the synthetic set and tests on the holdout. Membership inference re-fits the actual generator on each shadow model's member subset (8 shadow models per run) and attacks with nearest-neighbour distance.

What this does not show:

- **Neither generator is a real contender.** Both sample empirical marginals; `independent_marginals` has no feature dependence at all and exists as a floor. CTGAN/TVAE and the diffusion model don't exist yet, so nothing here says anything about the project's actual comparison.
- **The holdout is very small.** 6 positives, all among the 20 non-Puerto-Rican rows (see [`baseline_generator_result.md`](baseline_generator_result.md)). Utility differences of 0.1 are inside one standard deviation.
- **The membership numbers depend on which attack is run.** The original attack sees 4 numeric columns and reads 0.51 to 0.52. Attacks on all columns and on ICD-9 code sets read 0.55 to 0.64 and are calibrated against a ceiling and floor in [`membership_calibration_result.md`](membership_calibration_result.md). All are shadow-model AUROCs, a proxy for attacking the real synthetic files.
- **p-values here are over generator seeds on one fixed dataset and holdout.** They say nothing about a different sample of patients, and the five tests are not corrected for multiple comparisons.
- **Not reproduced across machines.** Track 1 reports copula seed-42 TSTR of 0.356 (LR) and 0.724 (RF); I get 0.931 and 0.672 for the same seed with the same `utility_eval.py`, and I get the same numbers on rerun. Fidelity agrees closely (JSD 0.0189 vs 0.016). The copula's output depends on the numpy build, traced to `method="eigh"` in its sampler (P-008 and P-009 in [`problems_and_decisions.md`](problems_and_decisions.md)); which numpy Track 1 ran is unconfirmed. My environment is Python 3.11.9, numpy 2.4.6, scikit-learn 1.8.0, scipy 1.17.1.

**Honest phrasing for the report: "the harness runs end to end on real synthetic data and separates a signal-free generator from a dependence-preserving one only weakly; the baselines are not distinguishable on fidelity marginals, borderline on utility, and a 4-column membership attack shows no leak while attacks on all columns and on ICD-9 code sets do (0.58 and 0.64 for the copula)."**

---

## Results (mean ± sd over 20 seeds)

| Metric | `gaussian_copula` | `independent_marginals` | Welch p | Reference |
|---|---|---|---|---|
| Mean JS divergence vs train | 0.0189 ± 0.0013 | 0.0183 ± 0.0008 | 0.115 | real-vs-real floor 0.099 |
| Correlation diff vs train | 0.1355 ± 0.0028 | 0.1629 ± 0.0026 | < 0.0001 | real-vs-real floor 0.203 |
| KS pass fraction | 0.9989 ± 0.0049 | 1.0000 ± 0.0000 | | |
| TSTR AUROC, logistic regression | 0.628 ± 0.219 | 0.493 ± 0.196 | 0.046 | TRTR 0.578 |
| TSTR AUROC, random forest | 0.621 ± 0.149 | 0.480 ± 0.174 | 0.009 | TRTR 0.737 |
| Membership AUROC, 4 numeric columns | 0.522 ± 0.027 | 0.507 ± 0.034 | 0.121 | protocol band 0.45 to 0.55 |
| Membership AUROC, Gower (all columns) | 0.583 ± 0.021 | 0.551 ± 0.030 | 0.0004 | floor 0.503 |
| Membership AUROC, ICD-9 code sets | 0.639 ± 0.016 | 0.638 ± 0.016 | | floor 0.489, fail line 0.65 |
| Attribute inference uplift, ethnicity (superseded) | 0.0000 ± 0.0000 | 0.0000 ± 0.0000 | | see P-003 |
| Attribute inference, age bucket: member gap | −0.001 ± 0.090 | −0.021 ± 0.083 | | ceiling 0.571 |
| Attribute inference, first care unit: member gap | 0.009 ± 0.019 | −0.003 ± 0.016 | | ceiling 0.768 |
| Attribute inference, gender: member gap | 0.056 ± 0.114 | 0.062 ± 0.092 | | ceiling 0.620; set-composition bias, P-011 |

Reading it:

| Question | Answer from these 40 runs |
|---|---|
| Do the generators differ on marginal fidelity? | No. Both copy empirical marginals, so both sit near 0.018. |
| Does the copula preserve more correlation? | Yes, but by 0.027 out of a noise floor of 0.203. It is a real difference and a small one. |
| Does the copula preserve more utility signal? | Probably, at about 0.14 AUROC higher, but the p-values are 0.046 and 0.009 before correction and the seed sd is 0.15 to 0.22. Suggestive, not established. |
| Is either generator outside the privacy band? | On the 4-column attack no (copula 0.522, one-sample p = 0.002; independent 0.507, p = 0.40). On the stronger attacks yes: Gower reads 0.583 and 0.551, and ICD-9 code sets read 0.639 and 0.638, close to the 0.65 fail line. The 4-column result understated the leak; see [`membership_calibration_result.md`](membership_calibration_result.md). |
| Is the attribute-inference result informative? | The ethnicity number no (P-003). On attributes both splits cover, neither baseline shows a member gap beyond the no-dependence control, but the attack only detects memorization on this dataset; see [`attribute_targets_result.md`](attribute_targets_result.md). |

---

## Raw evidence

```
$ python summarize_results.py
gaussian_copula  (n_seeds=20)
  mean_js                      0.0189 +/- 0.0013
  corr_diff                    0.1355 +/- 0.0028
  ks_pass                      0.9989 +/- 0.0049
  mia_auroc                    0.5220 +/- 0.0271
  attr_uplift                  0.0000 +/- 0.0000
  tstr_logistic_regression     0.6284 +/- 0.2190
  gap_logistic_regression      -0.0507 +/- 0.2190
  tstr_random_forest           0.6210 +/- 0.1493
  gap_random_forest            0.1163 +/- 0.1493
independent_marginals  (n_seeds=20)
  mean_js                      0.0183 +/- 0.0008
  corr_diff                    0.1629 +/- 0.0026
  ks_pass                      1.0000 +/- 0.0000
  mia_auroc                    0.5066 +/- 0.0339
  attr_uplift                  0.0000 +/- 0.0000
  tstr_logistic_regression     0.4925 +/- 0.1963
  gap_logistic_regression      0.0852 +/- 0.1963
  tstr_random_forest           0.4796 +/- 0.1744
  gap_random_forest            0.2577 +/- 0.1744
```

```
Welch t-tests, copula vs independent_marginals, 20 seeds each
tstr_lr    copula 0.6284 indep 0.4925 diff +0.1359 welch p=0.0457
tstr_rf    copula 0.6210 indep 0.4796 diff +0.1414 welch p=0.0091
corr_diff  copula 0.1355 indep 0.1629 diff -0.0274 welch p=0.0000
mean_js    copula 0.0189 indep 0.0183 diff +0.0006 welch p=0.1152
mia        copula 0.5220 indep 0.5066 diff +0.0154 welch p=0.1205
gaussian_copula MIA vs 0.5: mean 0.5220 p=0.0018
independent_marginals MIA vs 0.5: mean 0.5066 p=0.3964
```

---

## Contrast with the stand-in results

Every earlier Track 2 number used real train as a fake "synthetic" set. The fidelity floor there (mean JSD 0.099 against holdout) is now the reference for real generators rather than a generator result. The membership scores changed meaning too: the stand-in run measured a deliberately memorizing generator (0.82); this run attacks generators that were actually fit and sampled, and finds 0.52 and 0.51.
