# Positive Control Result — the attacks catch TVAE, every generator leaks through once-seen ICD-9 codes, and TVAE leaks through typical rows (2026-09-24)

Raw evidence that the membership attacks detect a generator Track 1 verified memorizes, what the ceiling and floor look like for seven arms, and where each generator's leakage comes from. Reproduce with `python -m evaluation.mia_calibration`, `python -m evaluation.mia_direct_check`, `python -m evaluation.mia_count_check` and `python -m evaluation.synthetic_coverage`, after the runs in [`full_evaluation_result.md`](full_evaluation_result.md). This extends [`membership_calibration_result.md`](membership_calibration_result.md).

---

## Method (honest framing)

Seven arms: the two controls (`exact_copy` returns its training rows, the ceiling; `disjoint_real` returns real holdout rows it never saw, the floor) and the five arms of the full evaluation. TVAE is the positive control Track 1 proposed (ADR-024), because its sweep found 52 to 71% of its rows are near-copies of training rows.

Five attacks, each a nearest-neighbour distance from a train record to a synthetic set, turned into a score by leave-one-shadow-out logistic regression over 8 shadow generators, 20 seeds (42 to 61): `numeric4` (4 numeric columns), `gower` (all 53 features), `icd9_codes` (Jaccard on code sets), and two diagnostics that use train code frequencies an attacker would not have, `codes_once` (only the 286 codes seen once in train) and `codes_repeated` (only the 197 seen twice or more). Pooled true-positive rates at 5% and 1% false-positive rate come from the pooled held-out predictions of all shadow worlds. The per-record report is, for the code-set attack, each record's mean distance when it was a non-member minus when it was a member, averaged over seeds.

What this does not show:

- **One positive control.** TVAE is a single generator on a single 94-row dataset, so "the attacks catch it" is one detection, not a detection rate.
- **Track 1's memorization measure and mine are different.** His asks how close each *synthetic* row is to the training set; mine asks how close each *training* row is to the synthetic set. The coverage check below suggests why the two read differently, but that is one supporting measurement.
- **The direct attack on the real target is still inconclusive.** The generator fitted on all 94 rows has no valid non-members, because the holdout differs in distribution, so its intervals are wide.
- **The per-record report is descriptive.** 94 records, averaged over 20 seeds, with a no-leak floor that is itself positive (0.178).
- **Shadow generators are fitted on 47 rows,** half the size of the target generator.

**Honest phrasing for the report: "the membership attacks separate a generator known to memorize from the others on the all-column and code-set attacks and not on a 4-column attack; every generator that emits codes it saw leaks through codes seen once in train, so that channel is not a property of any one model; TVAE additionally leaks through ordinary rows because it collapses onto about a third of the training rows."**

---

## Results

### Shadow-model AUROC (mean ± sd over 20 seeds)

| Arm | `numeric4` | `gower` | `icd9_codes` | `codes_once` (diag.) | `codes_repeated` (diag.) |
|---|---|---|---|---|---|
| `exact_copy` (ceiling) | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 0.992 ± 0.000 | 0.995 ± 0.002 |
| `disjoint_real` (floor) | 0.502 ± 0.028 | 0.503 ± 0.032 | 0.489 ± 0.030 | 0.481 ± 0.028 | 0.489 ± 0.027 |
| `independent_marginals` | 0.507 ± 0.034 | 0.551 ± 0.030 | 0.638 ± 0.016 | 0.839 ± 0.014 | 0.617 ± 0.018 |
| `gaussian_copula` | 0.515 ± 0.036 | 0.585 ± 0.017 | 0.645 ± 0.019 | 0.836 ± 0.013 | 0.624 ± 0.016 |
| `gaussian_copula_shrink025` | 0.518 ± 0.038 | 0.617 ± 0.021 | 0.651 ± 0.020 | 0.838 ± 0.010 | 0.629 ± 0.016 |
| `ctgan` | 0.507 ± 0.022 | 0.541 ± 0.029 | 0.637 ± 0.016 | 0.834 ± 0.013 | 0.615 ± 0.016 |
| `tvae` | 0.503 ± 0.033 | **0.649 ± 0.016** | **0.680 ± 0.018** | 0.821 ± 0.013 | **0.647 ± 0.019** |

### Pooled true-positive rate at low false-positive rate

| Arm | `gower` at 5% FPR | `gower` at 1% FPR | `icd9_codes` at 5% FPR | `icd9_codes` at 1% FPR |
|---|---|---|---|---|
| `exact_copy` (ceiling) | 1.000 | 1.000 | 1.000 | 1.000 |
| `disjoint_real` (floor; chance 0.05 and 0.01) | 0.045 | 0.009 | 0.045 | 0.009 |
| `independent_marginals` | 0.064 | 0.014 | 0.114 | 0.029 |
| `gaussian_copula` | 0.093 | 0.019 | 0.119 | 0.028 |
| `gaussian_copula_shrink025` | 0.123 | 0.038 | 0.144 | 0.039 |
| `ctgan` | 0.059 | 0.013 | 0.114 | 0.025 |
| `tvae` | **0.187** | **0.058** | **0.163** | **0.048** |

### Where the leakage sits, per record (code-set attack)

| Arm | Spearman of record advantage vs number of once-seen codes | Once-seen codes per record, top 10% most exposed | Rest |
|---|---|---|---|
| `exact_copy` | 0.470 | 5.10 | 2.80 |
| `disjoint_real` (no-leak floor) | 0.178 | 3.20 | 3.02 |
| `independent_marginals` | 0.278 | 4.90 | 2.82 |
| `gaussian_copula` | 0.258 | 5.20 | 2.79 |
| `gaussian_copula_shrink025` | 0.204 | 4.60 | 2.86 |
| `ctgan` | 0.223 | 5.60 | 2.74 |
| `tvae` | −0.011 | 2.20 | 3.14 |

### How many training rows does each generator sit closest to?

| Arm | Distinct train rows nearest to some synthetic row (of 94) | Most synthetic rows nearest to a single train row |
|---|---|---|
| `independent_marginals` | 41.1 ± 3.1 | 13.6 ± 2.9 |
| `gaussian_copula` | 45.1 ± 2.4 | 10.4 ± 2.5 |
| `gaussian_copula_shrink025` | 47.1 ± 3.6 | 8.3 ± 1.7 |
| `ctgan` | 39.9 ± 3.1 | 12.0 ± 3.2 |
| `tvae` | **31.2 ± 3.6** | **24.0 ± 4.9** |

### Direct attack on the real synthetic files (20 seeds)

Members are the 94 train rows, non-members are holdout rows, score is the negative distance to the nearest synthetic row. Brackets are 95% bootstrap intervals over rows.

| Arm | Attack | vs all holdout (35) | vs non-PR holdout (20) |
|---|---|---|---|
| `independent_marginals` | `gower` | 0.622 [0.519, 0.724] | 0.469 [0.346, 0.596] |
| `independent_marginals` | `icd9_codes` | 0.519 [0.418, 0.618] | 0.605 [0.474, 0.725] |
| `gaussian_copula` | `gower` | 0.642 [0.549, 0.740] | 0.493 [0.370, 0.621] |
| `gaussian_copula` | `icd9_codes` | 0.514 [0.423, 0.617] | 0.599 [0.470, 0.716] |
| `gaussian_copula_shrink025` | `gower` | 0.662 [0.558, 0.749] | 0.516 [0.381, 0.638] |
| `gaussian_copula_shrink025` | `icd9_codes` | 0.531 [0.426, 0.631] | 0.612 [0.497, 0.722] |
| `ctgan` | `gower` | 0.612 [0.508, 0.713] | 0.446 [0.318, 0.578] |
| `ctgan` | `icd9_codes` | 0.511 [0.415, 0.607] | 0.592 [0.469, 0.700] |
| `tvae` | `gower` | 0.692 [0.578, 0.786] | 0.545 [0.418, 0.668] |
| `tvae` | `icd9_codes` | 0.575 [0.486, 0.660] | 0.609 [0.500, 0.722] |

Same-distribution diagnostic: the generator is fit on a random 47-row half of train, members are that half, and non-members are the other 47 train rows (no distribution shift), the 20 non-Puerto-Rican holdout rows, or all 35 holdout rows.

| Arm | Attack | vs other train half (47) | vs non-PR holdout (20) | vs all holdout (35) |
|---|---|---|---|---|
| `independent_marginals` | `gower` | 0.561 | 0.512 | 0.660 |
| `independent_marginals` | `icd9_codes` | 0.641 | 0.665 | 0.574 |
| `gaussian_copula` | `gower` | 0.594 | 0.537 | 0.678 |
| `gaussian_copula` | `icd9_codes` | 0.652 | 0.679 | 0.587 |
| `gaussian_copula_shrink025` | `gower` | 0.626 | 0.576 | 0.710 |
| `gaussian_copula_shrink025` | `icd9_codes` | 0.638 | 0.672 | 0.587 |
| `ctgan` | `gower` | 0.544 | 0.489 | 0.636 |
| `ctgan` | `icd9_codes` | 0.626 | 0.649 | 0.580 |
| `tvae` | `gower` | 0.675 | 0.606 | 0.729 |
| `tvae` | `icd9_codes` | 0.658 | 0.683 | 0.620 |

Ceiling control (synthetic = exact copy of train): 1.000 for both attacks against both non-member sets.

### Does a neighbourhood-count feature strengthen the attack? (3 seeds)

| Arm | Distance | Nearest and 3-nearest features | Plus count of synthetic rows within the 5th percentile radius |
|---|---|---|---|
| `gaussian_copula` | `gower` | 0.583 | 0.583 |
| `gaussian_copula` | `icd9_codes` | 0.648 | 0.647 |
| `tvae` | `gower` | 0.651 | 0.638 |
| `tvae` | `icd9_codes` | 0.679 | 0.679 |

| Reading | Evidence |
|---|---|
| The attacks are calibrated | Ceiling 1.000 and floor 0.48 to 0.50 on every attack; floor TPR 0.045 at 5% and 0.009 at 1% FPR |
| The positive control is detected | TVAE is highest on `gower` (0.649 vs 0.541 to 0.617), on `icd9_codes` (0.680 vs 0.637 to 0.651) and on pooled TPR at 1% FPR (0.058 vs 0.009 floor and 0.013 to 0.038 for the others) |
| The 4-column attack misses it | TVAE scores 0.503, the lowest of any generator and indistinguishable from the floor's 0.502 |
| Once-seen codes leak through every generator | `codes_once` is 0.821 to 0.839 for all five arms against a floor of 0.481, and CTGAN is at 0.834 despite learning no dependence, so this is a property of emitting codes seen in training |
| TVAE's extra leakage is elsewhere | `codes_repeated` 0.647 vs 0.615 to 0.629, and `gower` 0.649 vs 0.541 to 0.617 |
| TVAE does not leak through rare-code records | Its per-record advantage has Spearman −0.011 against once-seen codes, while the others sit at 0.20 to 0.28, only modestly above the no-leak floor of 0.178 |
| TVAE collapses onto about a third of the training rows | Its output is nearest to 31 of 94 train rows against 40 to 47 for the others, and up to 24 synthetic rows share one nearest train row against 8 to 14; this fits a moderate AUROC alongside a strong low-FPR rate |
| The same-distribution diagnostic agrees with the shadow numbers | `gower` 0.561, 0.594, 0.626, 0.544, 0.675 vs 0.551, 0.585, 0.617, 0.541, 0.649; code sets 0.626 to 0.658 vs 0.637 to 0.680 |
| The 15 Puerto Rican holdout rows inflate the `gower` attack | In the same-distribution diagnostic it reads 0.636 to 0.729 against all 35 holdout rows but 0.489 to 0.606 against the 20 non-Puerto-Rican rows, and 0.544 to 0.675 against the other half of train |
| The direct attack on the real target still cannot separate the arms | Every non-Puerto-Rican interval contains 0.5 or touches it, and none excludes the shadow value |
| A neighbourhood-count feature adds nothing | Changes of −0.013 to +0.000 in 3 seeds, so the attack is not leaving that kind of power unused |

---

## Raw evidence

```
$ python -m evaluation.mia_calibration
train ICD-9 codes: 286 seen once, 197 seen 2+ times; 6 workers

Mean shadow-model AUROC +/- sd over seeds
arm                                  numeric4            gower       icd9_codes       codes_once   codes_repeated
exact_copy                    1.000 +/- 0.000  1.000 +/- 0.000  1.000 +/- 0.000  0.992 +/- 0.000  0.995 +/- 0.002
disjoint_real                 0.502 +/- 0.028  0.503 +/- 0.032  0.489 +/- 0.030  0.481 +/- 0.028  0.489 +/- 0.027
independent_marginals         0.507 +/- 0.034  0.551 +/- 0.030  0.638 +/- 0.016  0.839 +/- 0.014  0.617 +/- 0.018
gaussian_copula               0.515 +/- 0.036  0.585 +/- 0.017  0.645 +/- 0.019  0.836 +/- 0.013  0.624 +/- 0.016
gaussian_copula_shrink025     0.518 +/- 0.038  0.617 +/- 0.021  0.651 +/- 0.020  0.838 +/- 0.010  0.629 +/- 0.016
ctgan                         0.507 +/- 0.022  0.541 +/- 0.029  0.637 +/- 0.016  0.834 +/- 0.013  0.615 +/- 0.016
tvae                          0.503 +/- 0.033  0.649 +/- 0.016  0.680 +/- 0.018  0.821 +/- 0.013  0.647 +/- 0.019

Pooled TPR at 5% FPR (chance 0.05)
arm                                  numeric4            gower       icd9_codes       codes_once   codes_repeated
exact_copy                    1.000 +/- 0.000  1.000 +/- 0.000  1.000 +/- 0.000  0.889 +/- 0.012  1.000 +/- 0.000
disjoint_real                 0.045 +/- 0.019  0.045 +/- 0.021  0.045 +/- 0.020  0.013 +/- 0.015  0.045 +/- 0.020
independent_marginals         0.053 +/- 0.026  0.064 +/- 0.021  0.114 +/- 0.017  0.044 +/- 0.017  0.101 +/- 0.023
gaussian_copula               0.057 +/- 0.018  0.093 +/- 0.027  0.119 +/- 0.023  0.052 +/- 0.022  0.111 +/- 0.019
gaussian_copula_shrink025     0.057 +/- 0.016  0.123 +/- 0.029  0.144 +/- 0.029  0.044 +/- 0.016  0.121 +/- 0.026
ctgan                         0.049 +/- 0.019  0.059 +/- 0.018  0.114 +/- 0.026  0.052 +/- 0.024  0.100 +/- 0.025
tvae                          0.042 +/- 0.015  0.187 +/- 0.031  0.163 +/- 0.028  0.052 +/- 0.021  0.134 +/- 0.026

Pooled TPR at 1% FPR (chance 0.01)
arm                                  numeric4            gower       icd9_codes       codes_once   codes_repeated
exact_copy                    1.000 +/- 0.000  1.000 +/- 0.000  1.000 +/- 0.000  0.873 +/- 0.010  0.764 +/- 0.202
disjoint_real                 0.010 +/- 0.008  0.009 +/- 0.010  0.009 +/- 0.007  0.000 +/- 0.001  0.007 +/- 0.007
independent_marginals         0.011 +/- 0.011  0.014 +/- 0.010  0.029 +/- 0.013  0.005 +/- 0.007  0.023 +/- 0.014
gaussian_copula               0.013 +/- 0.011  0.019 +/- 0.013  0.028 +/- 0.015  0.007 +/- 0.017  0.026 +/- 0.014
gaussian_copula_shrink025     0.009 +/- 0.007  0.038 +/- 0.020  0.039 +/- 0.016  0.005 +/- 0.012  0.031 +/- 0.014
ctgan                         0.010 +/- 0.008  0.013 +/- 0.008  0.025 +/- 0.016  0.008 +/- 0.014  0.021 +/- 0.010
tvae                          0.009 +/- 0.007  0.058 +/- 0.021  0.048 +/- 0.019  0.005 +/- 0.012  0.033 +/- 0.019

Per-record advantage of the icd9_codes attack (mean over seeds), vs singleton codes per record
arm                           spearman   top-10% singleton codes    rest
exact_copy                       0.470                      5.10    2.80
disjoint_real                    0.178                      3.20    3.02
independent_marginals            0.278                      4.90    2.82
gaussian_copula                  0.258                      5.20    2.79
gaussian_copula_shrink025        0.204                      4.60    2.86
ctgan                            0.223                      5.60    2.74
tvae                            -0.011                      2.20    3.14
```

```
$ python -m evaluation.synthetic_coverage
arm                           distinct train rows hit (of 94)    max synthetic rows on one train row
independent_marginals                        41.1 +/-  3.1                      13.6 +/-  2.9
gaussian_copula                              45.1 +/-  2.4                      10.4 +/-  2.5
gaussian_copula_shrink025                    47.1 +/-  3.6                       8.3 +/-  1.7
ctgan                                        39.9 +/-  3.1                      12.0 +/-  3.2
tvae                                         31.2 +/-  3.6                      24.0 +/-  4.9
```

```
$ python -m evaluation.mia_count_check
arm                          distance     min + knn3   + count   (mean AUROC over 3 seeds)
gaussian_copula              gower             0.583     0.583
gaussian_copula              icd9_codes        0.648     0.647
tvae                         gower             0.651     0.638
tvae                         icd9_codes        0.679     0.679
```

The direct-check output is the two tables above, produced by `python -m evaluation.mia_direct_check`.

---

## Contrast with the two-baseline calibration

[`membership_calibration_result.md`](membership_calibration_result.md) had no generator known to leak, so it could show the attacks were calibrated but not that they detect a real memorizer. TVAE supplies that. It also changes one reading: the once-seen-code channel there looked like a property of the two baselines, and it now appears in CTGAN and TVAE too, so it is a property of any generator that reproduces codes it saw in training.
