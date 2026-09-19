# Membership Calibration Result — the 4-column attack missed a leak that ICD-9 codes carry (2026-09-19)

Raw evidence that the membership attack has a known ceiling and floor, and that both baselines leak through ICD-9 codes. Reproduce with `python mia_calibration.py` (about a minute) and `python mia_direct_check.py` (about 20 seconds).

---

## Method (honest framing)

Every number below is a shadow-model AUROC: 8 shadow generators are fit on random 47-row member subsets of the 94 train rows, and the attack is scored leave-one-shadow-out. Five attacks are compared, each a nearest-neighbour distance from a train record to a synthetic set:

| Attack | Distance over | Realistic attacker? |
|---|---|---|
| `numeric4` | `age`, `los_hospital_days`, `los_icu_days`, `n_diagnoses` | Yes (the original attack) |
| `gower` | all 53 features (44 numeric and lab, 8 categorical and binary, ICD-9 code set), equal weight | Yes |
| `icd9_codes` | Jaccard distance between ICD-9 code sets | Yes |
| `codes_once` | same, keeping only the 286 codes that appear in exactly one train row | **No, a diagnostic** |
| `codes_repeated` | same, keeping only the 197 codes that appear in 2+ train rows | **No, a diagnostic** |

The last two use train code frequencies, which an attacker doesn't have. They exist to locate the leak, not to score a generator.

Four arms are attacked: `exact_copy` (returns its training rows, the ceiling), `disjoint_real` (returns real holdout rows it never saw, the floor), and the two Track 1 baselines. All use 20 seeds (42 to 61).

What this does not show:

- **The explanation for the leak is supported, not proven.** Codes seen once in train carry the signal, which fits the fact that a generator can only emit codes it saw during fitting, so a non-member's unique code cannot appear in the synthetic data. I did not test a generator that suppresses rare codes.
- **Neither baseline is meant to be private.** Both sample empirical marginals. The blueprint's 0.50 target applies to the privacy-preserving generators, which don't exist yet.
- **These are shadow-model numbers, generators fit on 47 rows.** A direct attack on a generator fit on all 94 rows has no valid non-members (the holdout differs in distribution), so its intervals are wide. The direct check below is consistent with the shadow numbers and cannot confirm them by itself.
- **Seeds resample the generators, not the patients.** All 40 runs share the same 94 train rows and the same 35-row holdout.

**Honest phrasing for the report: "on a 94-row train set both baselines are separable from non-members mainly through the rare ICD-9 codes they reproduce, at a mean shadow-model AUROC of 0.64 on code sets (individual seeds up to 0.68), while an attack on four numeric columns reads 0.51 to 0.52 and would have wrongly suggested no leak."**

---

## Results

### Calibration (mean ± sd over 20 seeds)

| Arm | `numeric4` | `gower` | `icd9_codes` | `codes_once` (diagnostic) | `codes_repeated` (diagnostic) |
|---|---|---|---|---|---|
| `exact_copy` (ceiling) | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 0.992 ± 0.000 | 0.995 ± 0.002 |
| `disjoint_real` (floor) | 0.502 ± 0.028 | 0.503 ± 0.032 | 0.489 ± 0.030 | 0.481 ± 0.028 | 0.489 ± 0.027 |
| `independent_marginals` | 0.507 ± 0.034 | 0.551 ± 0.030 | 0.638 ± 0.016 | 0.839 ± 0.014 | 0.617 ± 0.018 |
| `gaussian_copula` | 0.522 ± 0.027 | 0.583 ± 0.021 | 0.639 ± 0.016 | 0.840 ± 0.015 | 0.620 ± 0.015 |

| Reading | Evidence |
|---|---|
| The attack works and is calibrated | Ceiling 1.000 and floor 0.49 to 0.50 on every attack, with the floor's seed sd at about 0.03 |
| `numeric4` was too weak to see the leak | 0.507 and 0.522 are within one floor sd of the floor mean (0.502 ± 0.028) |
| `icd9_codes` separates both baselines from the floor on every seed | Baseline range 0.604 to 0.676, floor range 0.437 to 0.546 |
| The leak is concentrated in rare codes | `codes_once` 0.84 vs `codes_repeated` 0.62, for both generators |
| Dependence modelling makes no difference to the code leak | Copula 0.639 vs independent 0.638 |
| Where the protocol's bands put this | The old bands were "good" 0.45 to 0.55 and "fail" 0.65 and above. Mean `icd9_codes` is 0.64, and seeds reach 0.667 and 0.676, so it straddles the fail line |

### Direct check on the real synthetic files (with intervals and a shift diagnostic)

Score = negative distance to the nearest synthetic row, AUROC of members vs non-members, no shadow models, mean over 20 seeds. Members and non-members are scored in one distance call (see P-012).

**Target generator, fit on all 94 train rows.** Non-members are holdout rows. Brackets are 95% bootstrap intervals that resample the member and non-member rows, which seed sd cannot capture.

| Generator | Attack | vs all holdout (35) | vs non-PR holdout (20) |
|---|---|---|---|
| `independent_marginals` | `gower` | 0.622 [0.519, 0.724] | 0.469 [0.346, 0.596] |
| `independent_marginals` | `icd9_codes` | 0.519 [0.418, 0.618] | 0.605 [0.474, 0.725] |
| `gaussian_copula` | `gower` | 0.648 [0.555, 0.743] | 0.492 [0.367, 0.624] |
| `gaussian_copula` | `icd9_codes` | 0.505 [0.415, 0.605] | 0.603 [0.481, 0.716] |

**Shift diagnostic.** The generator is fit on a random 47-row half of train and its members are that half. The other 47 train rows are non-members from the same distribution.

| Generator | Attack | vs other train half (47) | vs non-PR holdout (20) | vs all holdout (35) |
|---|---|---|---|---|
| `independent_marginals` | `gower` | 0.561 | 0.512 | 0.660 |
| `independent_marginals` | `icd9_codes` | 0.641 | 0.665 | 0.574 |
| `gaussian_copula` | `gower` | 0.589 | 0.531 | 0.676 |
| `gaussian_copula` | `icd9_codes` | 0.627 | 0.658 | 0.578 |

Ceiling control (synthetic = exact copy of train): 1.000 for both attacks against both non-member sets.

| Reading | Evidence |
|---|---|
| The 15 Puerto Rican rows inflate the Gower score | Against the same-distribution half it reads 0.561 and 0.589; against all holdout rows 0.660 and 0.676, about +0.10 |
| The code-set attack is not inflated the same way | Same-distribution half 0.641 and 0.627, all holdout 0.574 and 0.578 (lower), non-PR holdout 0.665 and 0.658 |
| The same-distribution check agrees with the shadow numbers | Gower 0.561 and 0.589 vs 0.551 and 0.583; code sets 0.641 and 0.627 vs 0.638 and 0.639 |
| The direct check on the real target cannot confirm the leak | Code sets vs non-PR holdout gives 0.605 [0.474, 0.725] and 0.603 [0.481, 0.716], which contains both 0.5 and 0.64. Gower vs non-PR gives 0.469 to 0.492 with intervals containing both 0.5 and the shadow value |
| Not measured | The AUROC for a generator fit on all 94 rows against valid non-members, because none exist |

---

## Raw evidence

```
$ python mia_calibration.py
train ICD-9 codes: 286 seen once, 197 seen 2+ times
arm                                numeric4              gower         icd9_codes         codes_once     codes_repeated
exact_copy                  1.000 +/- 0.000    1.000 +/- 0.000    1.000 +/- 0.000    0.992 +/- 0.000    0.995 +/- 0.002
disjoint_real               0.502 +/- 0.028    0.503 +/- 0.032    0.489 +/- 0.030    0.481 +/- 0.028    0.489 +/- 0.027
independent_marginals       0.507 +/- 0.034    0.551 +/- 0.030    0.638 +/- 0.016    0.839 +/- 0.014    0.617 +/- 0.018
gaussian_copula             0.522 +/- 0.027    0.583 +/- 0.021    0.639 +/- 0.016    0.840 +/- 0.015    0.620 +/- 0.015
```

```
per-seed ranges vs the floor's range (20 seeds each)
gower           independent_marginals  range 0.464-0.623 | floor range 0.435-0.542 | separated: False
gower           gaussian_copula        range 0.539-0.618 | floor range 0.435-0.542 | separated: False
icd9_codes      independent_marginals  range 0.604-0.667 | floor range 0.437-0.546 | separated: True
icd9_codes      gaussian_copula        range 0.611-0.676 | floor range 0.437-0.546 | separated: True
codes_once      independent_marginals  range 0.812-0.865 | floor range 0.438-0.528 | separated: True
codes_once      gaussian_copula        range 0.816-0.875 | floor range 0.438-0.528 | separated: True
codes_repeated  independent_marginals  range 0.585-0.653 | floor range 0.444-0.529 | separated: True
codes_repeated  gaussian_copula        range 0.602-0.658 | floor range 0.444-0.529 | separated: True
```

```
$ python mia_direct_check.py
1. Target generator (fit on all 94 train rows), mean AUROC [95% bootstrap interval], 20 seeds
   generator              attack           vs all holdout (35)     vs non-PR holdout (20)
   independent_marginals  gower           0.622 [0.519, 0.724]       0.469 [0.346, 0.596]
   independent_marginals  icd9_codes      0.519 [0.418, 0.618]       0.605 [0.474, 0.725]
   gaussian_copula        gower           0.648 [0.555, 0.743]       0.492 [0.367, 0.624]
   gaussian_copula        icd9_codes      0.505 [0.415, 0.605]       0.603 [0.481, 0.716]

2. Shift diagnostic (generator fit on a random 47-row half of train), mean AUROC over 20 seeds
   generator              attack        vs other train half (47)   vs non-PR holdout (20)   vs all holdout (35)
   independent_marginals  gower                            0.561                    0.512                 0.660
   independent_marginals  icd9_codes                       0.641                    0.665                 0.574
   gaussian_copula        gower                            0.589                    0.531                 0.676
   gaussian_copula        icd9_codes                       0.627                    0.658                 0.578

3. Ceiling control (synthetic = exact copy of train)
   gower       vs all holdout 1.000 | vs non-PR holdout 1.000
   icd9_codes  vs all holdout 1.000 | vs non-PR holdout 1.000
```

---

## Contrast with the baseline evaluation

[`baseline_evaluation_result.md`](baseline_evaluation_result.md) reported membership AUROC of 0.522 and 0.507 and concluded both generators sat inside the privacy band. That was true of the 4-column attack and misleading as a privacy statement, because the attack could not see the code-set leak. The same run with the Gower attack gives 0.583 and 0.551, and with code sets alone 0.639 and 0.638.
