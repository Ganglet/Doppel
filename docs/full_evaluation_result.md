# Full Evaluation Result — TVAE reaches the real-data utility ceiling by copying, CTGAN learns nothing, and no arm dominates (2026-09-24)

Raw evidence for the first evaluation of all of Track 1's generator families (statistical, GAN-family, VAE) through the full Track 2 harness. Reproduce with `pip install -r generators/requirements-neural.txt`, then `python -m evaluation.eval_runner --generator <arm> --seed <n>` for seeds 42 to 61 and every arm in [`evaluation/arms.py`](../evaluation/arms.py), then `python -m evaluation.summarize_results`. This supersedes the two-arm numbers in [`baseline_evaluation_result.md`](baseline_evaluation_result.md).

---

## Method (honest framing)

Five arms, each fitted on the 94 train rows and run over 20 seeds (42 to 61), 100 runs in total. The configs are the ones Track 1 carried out of its initial sweep (ADR-024), not tuned by me.

| Arm | Config | Role |
|---|---|---|
| `independent_marginals` | none | no-dependence floor |
| `gaussian_copula` | Ledoit-Wolf shrinkage | Phase 1 statistical baseline |
| `gaussian_copula_shrink025` | shrinkage 0.25 | the copula config Track 1 carried into Phase 3 |
| `ctgan` | 300 epochs | least-bad CTGAN config in Track 1's sweep |
| `tvae` | 300 epochs | verifiably memorizes (52 to 71% near-copies in Track 1's sweep), used as the membership-attack positive control |

Environment for every run: Python 3.11.9, numpy 2.4.6, pandas 2.3.3, scikit-learn 1.8.0, scipy 1.17.1, torch 2.14.0+cpu, ctgan 0.12.1, rdt 1.22.0 (Track 1's pins). Metrics are as in [`eval_protocol.md`](../eval_protocol.md): fidelity against real train, utility as TSTR on `hospital_expire_flag` against the 35-row real holdout, membership inference with 8 shadow generators and three attacks, attribute inference on `gender`, `first_careunit` and `age_bucket`.

What this does not show:

- **The neural configs are untuned.** Track 1's next sweep tests smaller CTGAN and TVAE networks and stronger regularisation, so the neural rows may move. They need a rerun when it lands.
- **No diffusion model.** It doesn't exist yet, so this is two of the blueprint's three families.
- **The dataset is tiny.** 94 train rows and a 35-row holdout with 6 positives. Seeds resample the generators, not the patients, and every p-value below is uncorrected and only reflects seed variation.
- **TVAE's utility is copied signal.** Its TSTR matches the real-data ceiling because it reproduces real training rows, so it should not be read as "TVAE preserves utility well".
- **Cross-machine reproducibility of the neural arms is only partly checked.** TVAE and CTGAN seed 42 are both byte-identical under torch 2.12.0 and 2.14.0 on this machine. Other machines and other seeds are untested.
- **Not comparable to the Phase 2 numbers.** Mean JSD dropped from about 0.019 to 0.016 because I fixed a dtype bug that distorted `icd9_primary` (P-014), and the copula's rows are new draws since Track 1's Cholesky fix.
- **Cost.** One CTGAN fit on 94 rows takes 48 s alone on this laptop but about 6.8 minutes with six running at once, so the 100 runs were slow and CTGAN accounted for most of the time (P-016). Total wall-clock was not timed.

**Honest phrasing for the report: "on 94 training rows the statistical baseline matches or beats both neural generators on fidelity and privacy, TVAE matches the real-data utility ceiling only by copying training rows, CTGAN produces data no more useful or more private than independent marginals, and no arm dominates on fidelity, utility and privacy together; the neural configs are untuned and the diffusion model is not yet evaluated."**

---

## Results (mean ± sd over 20 seeds)

| Metric | `independent_marginals` | `gaussian_copula` | `gaussian_copula_shrink025` | `ctgan` | `tvae` |
|---|---|---|---|---|---|
| Mean JS divergence vs train | 0.0162 ± 0.0007 | 0.0165 ± 0.0009 | 0.0165 ± 0.0010 | 0.0937 ± 0.0127 | 0.1063 ± 0.0039 |
| Correlation diff vs train | 0.1629 ± 0.0026 | 0.1376 ± 0.0037 | 0.1098 ± 0.0045 | 0.1653 ± 0.0019 | 0.1224 ± 0.0028 |
| KS pass fraction | 1.000 ± 0.000 | 1.000 ± 0.000 | 0.999 ± 0.005 | 0.328 ± 0.068 | 0.501 ± 0.047 |
| TSTR AUROC, logistic regression | 0.493 ± 0.196 | 0.587 ± 0.178 | 0.634 ± 0.201 | 0.473 ± 0.153 | 0.670 ± 0.144 |
| TSTR AUROC, random forest | 0.480 ± 0.174 | 0.599 ± 0.202 | 0.684 ± 0.183 | 0.546 ± 0.132 | 0.738 ± 0.096 |
| Membership AUROC, 4 numeric columns | 0.507 ± 0.034 | 0.515 ± 0.036 | 0.518 ± 0.038 | 0.507 ± 0.022 | 0.503 ± 0.033 |
| Membership AUROC, Gower | 0.551 ± 0.030 | 0.585 ± 0.017 | 0.617 ± 0.021 | 0.541 ± 0.029 | 0.649 ± 0.016 |
| Membership AUROC, ICD-9 codes | 0.638 ± 0.016 | 0.645 ± 0.019 | 0.651 ± 0.020 | 0.637 ± 0.016 | 0.680 ± 0.018 |
| Membership worst case | 0.638 ± 0.016 | 0.645 ± 0.019 | 0.651 ± 0.020 | 0.637 ± 0.016 | 0.680 ± 0.018 |
| Pooled TPR at 1% FPR, Gower (chance 0.01) | 0.014 | 0.019 | 0.038 | 0.013 | 0.058 |
| Pooled TPR at 5% FPR, Gower (chance 0.05) | 0.064 | 0.093 | 0.123 | 0.059 | 0.187 |

Real-data references from the same runs: TRTR AUROC 0.578 (logistic regression) and 0.737 (random forest); real train vs holdout mean JSD 0.099 and correlation diff 0.203.

Attribute inference member gap (member uplift minus non-member uplift, read against `independent_marginals`, which has no dependence to exploit):

| Target | `independent_marginals` | `gaussian_copula` | `gaussian_copula_shrink025` | `ctgan` | `tvae` |
|---|---|---|---|---|---|
| `gender` | 0.042 ± 0.099 | 0.079 ± 0.106 | 0.119 ± 0.128 (p = 0.041) | 0.004 ± 0.090 | **0.183 ± 0.126** (p = 0.0004) |
| `first_careunit` | −0.005 ± 0.020 | 0.004 ± 0.020 | 0.004 ± 0.039 | −0.003 ± 0.027 | 0.008 ± 0.019 (p = 0.042) |
| `age_bucket` | −0.019 ± 0.086 | 0.024 ± 0.098 | 0.061 ± 0.084 (p = 0.005) | −0.007 ± 0.084 | 0.041 ± 0.058 (p = 0.014) |

p-values in that table are Welch tests against `independent_marginals`, uncorrected across 12 tests.

| Reading | Evidence |
|---|---|
| Both neural generators lose on marginal fidelity | Mean JSD 0.094 and 0.106 vs 0.0165 for the copulas; CTGAN vs independent p < 0.001 |
| CTGAN has learned no dependence and adds no utility or privacy over the floor | Correlation diff 0.165 vs the floor's 0.163; TSTR RF +0.067 (p = 0.18); worst-case membership −0.001 (p = 0.84) |
| TVAE sits at the real-data utility ceiling | TSTR RF 0.738 vs TRTR 0.737, logistic regression 0.670 vs 0.578 |
| TVAE leaks the most, on every attack that can see it | Worst case 0.680 vs 0.637 to 0.651 (p < 0.0001 against each arm); Gower TPR at 1% FPR 0.058, about 6× chance; the largest attribute gap (gender 0.183) |
| The 4-column membership attack cannot see the leak | It scores TVAE at 0.503, the lowest of all five arms |
| The 0.25-shrinkage copula matches TVAE on utility with far better fidelity and less leakage | TSTR RF 0.684 vs 0.738 (p = 0.25), logistic regression 0.634 vs 0.670 (p = 0.51); JSD 0.0165 vs 0.1063; worst case 0.651 vs 0.680; Gower TPR at 1% 0.038 vs 0.058 (p = 0.004) |
| Less shrinkage buys correlation at a privacy cost | Copula 0.25 vs Ledoit-Wolf: correlation diff 0.110 vs 0.138, Gower AUROC +0.032 (p < 0.001), TPR at 1% +0.019 (p = 0.001), utility not significantly different (RF p = 0.18), worst case unchanged (+0.006, p = 0.30) |
| The attribute attack now detects memorization on a real generator | TVAE's gender gap is 4× the no-dependence control's; the earlier two-baseline run found no gap at all |

---

## Raw evidence

```
$ python -m evaluation.summarize_results   (selected rows)
ctgan  (n_seeds=20)
  mean_js                      0.0937 +/- 0.0127
  corr_diff                    0.1653 +/- 0.0019
  ks_pass                      0.3283 +/- 0.0683
  mia_auroc                    0.5072 +/- 0.0223
  mia_gower_auroc              0.5413 +/- 0.0289
  mia_codes_auroc              0.6370 +/- 0.0156
  mia_worst_case               0.6370 +/- 0.0156
  tstr_logistic_regression     0.4727 +/- 0.1527
  tstr_random_forest           0.5461 +/- 0.1316
gaussian_copula  (n_seeds=20)
  mean_js                      0.0165 +/- 0.0009
  corr_diff                    0.1376 +/- 0.0037
  ks_pass                      1.0000 +/- 0.0000
  mia_auroc                    0.5149 +/- 0.0363
  mia_gower_auroc              0.5850 +/- 0.0167
  mia_codes_auroc              0.6448 +/- 0.0188
  mia_worst_case               0.6448 +/- 0.0188
  tstr_logistic_regression     0.5871 +/- 0.1778
  tstr_random_forest           0.5994 +/- 0.2021
gaussian_copula_shrink025  (n_seeds=20)
  mean_js                      0.0165 +/- 0.0010
  corr_diff                    0.1098 +/- 0.0045
  ks_pass                      0.9989 +/- 0.0049
  mia_auroc                    0.5178 +/- 0.0377
  mia_gower_auroc              0.6167 +/- 0.0208
  mia_codes_auroc              0.6511 +/- 0.0197
  mia_worst_case               0.6511 +/- 0.0197
  tstr_logistic_regression     0.6336 +/- 0.2006
  tstr_random_forest           0.6836 +/- 0.1829
independent_marginals  (n_seeds=20)
  mean_js                      0.0162 +/- 0.0007
  corr_diff                    0.1629 +/- 0.0026
  ks_pass                      1.0000 +/- 0.0000
  mia_auroc                    0.5066 +/- 0.0339
  mia_gower_auroc              0.5508 +/- 0.0301
  mia_codes_auroc              0.6380 +/- 0.0156
  mia_worst_case               0.6380 +/- 0.0156
  tstr_logistic_regression     0.4925 +/- 0.1963
  tstr_random_forest           0.4796 +/- 0.1744
tvae  (n_seeds=20)
  mean_js                      0.1063 +/- 0.0039
  corr_diff                    0.1224 +/- 0.0028
  ks_pass                      0.5011 +/- 0.0470
  mia_auroc                    0.5030 +/- 0.0325
  mia_gower_auroc              0.6492 +/- 0.0163
  mia_codes_auroc              0.6796 +/- 0.0177
  mia_worst_case               0.6798 +/- 0.0175
  tstr_logistic_regression     0.6704 +/- 0.1437
  tstr_random_forest           0.7379 +/- 0.0961
```

```
Welch tests, tvae vs each arm (two-sided, uncorrected, 20 seeds each)
worst-case MIA  tvae 0.6798 | vs independent 0.6380 p=0.0000 | vs copula LW 0.6448 p=0.0000 | vs copula 0.25 0.6511 p=0.0000 | vs ctgan 0.6370 p=0.0000
gower TPR@1%    tvae 0.0577 | vs independent 0.0137 p=0.0000 | vs copula LW 0.0190 p=0.0000 | vs copula 0.25 0.0380 p=0.0042 | vs ctgan 0.0128 p=0.0000
TSTR RF         tvae 0.7379 | vs independent 0.4796 p=0.0000 | vs copula LW 0.5994 p=0.0100 | vs copula 0.25 0.6836 p=0.2494 | vs ctgan 0.5461 p=0.0000
TSTR LR         tvae 0.6704 | vs independent 0.4925 p=0.0024 | vs copula LW 0.5871 p=0.1117 | vs copula 0.25 0.6336 p=0.5095 | vs ctgan 0.4727 p=0.0001
mean JSD        tvae 0.1063 | vs independent 0.0162 p=0.0000 | vs copula LW 0.0165 p=0.0000 | vs copula 0.25 0.0165 p=0.0000 | vs ctgan 0.0937 p=0.0003
```

```
Pooled TPR at low FPR (mean over 20 seeds; chance 0.05 and 0.01)
arm                           gower@5%  gower@1%  codes@5%  codes@1%
independent_marginals            0.064     0.014     0.114     0.029
gaussian_copula                  0.093     0.019     0.119     0.028
gaussian_copula_shrink025        0.123     0.038     0.144     0.039
ctgan                            0.059     0.013     0.114     0.025
tvae                             0.187     0.058     0.163     0.048
```

---

## Contrast with the two-arm evaluation

[`baseline_evaluation_result.md`](baseline_evaluation_result.md) compared only the copula and `independent_marginals` and found no fidelity difference, a borderline utility edge for the copula, and no attribute gap. Adding the neural arms changes the picture in two ways: the fidelity axis now separates generators (the neural ones are 6× worse), and both the membership and attribute attacks detect the one generator known to memorize. The copula numbers themselves moved slightly, from the dtype fix (P-014) and new Cholesky draws.
