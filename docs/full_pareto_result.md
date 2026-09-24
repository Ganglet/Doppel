# Full Pareto Result — five arms are all non-dominated, and the frontier says more about the axes than about the generators (2026-09-24)

Raw evidence for the fidelity, utility and privacy frontier over Track 1's generator families, with the frontier re-derived under eight axis choices to test how much it depends on my choices. Reproduce with the runs in [`full_evaluation_result.md`](full_evaluation_result.md), then `python -m evaluation.pareto`. This supersedes [`pareto_result.md`](pareto_result.md), which covered two baselines.

---

## Method (honest framing)

Each arm is reduced to three numbers per seed over 20 seeds. An arm is on the frontier if no other arm is at least as good on every axis and strictly better on one, and frontier membership and pairwise dominance are bootstrapped over seeds (2,000 resamples).

| Axis | Definition | Better is |
|---|---|---|
| Fidelity | mean JS divergence vs real train, 52 columns | lower |
| Utility | mean of the logistic regression and random forest TSTR AUROC on `hospital_expire_flag` | higher |
| Privacy | `membership_worst_case`: the highest mean AUROC over the 4-column, Gower and ICD-9 code-set attacks | lower |

To validate the frontier I recompute it under seven other axis sets (adding a correlation axis, using one classifier, using one attack at a time, dropping utility) and check the privacy axis against the TVAE positive control.

What this does not show:

- **The genuine three-way comparison is incomplete.** The diffusion model does not exist yet, and the neural configs are Track 1's untuned carry-overs, so this is a frontier of a floor, two copula configs and two untuned neural generators.
- **Seed noise swamps most gaps.** Utility has a seed sd of 0.09 to 0.18, and the fidelity and privacy gaps between the non-neural arms are smaller than their seed sds.
- **The privacy axis currently measures ICD-9 code reproduction.** The code-set attack is the worst case in 98 of the 100 runs (all 20 for four arms, 18 of 20 for TVAE, where Gower wins the other two).
- **Bootstrap probabilities are over generator seeds on one dataset,** not over patients.
- **No plot.** A chart for the report waits for Phase 4.

**Honest phrasing for the report: "with five arms and this much seed variation every arm is non-dominated; the frontier shows the direction of each trade-off (TVAE buys utility with fidelity and privacy, the copulas sit between, CTGAN and independent marginals leak least and preserve least) and does not support ranking the generators."**

---

## Results

| Arm | Seeds | Fidelity (JS) | Utility (TSTR) | Privacy (worst MIA AUROC) | On frontier | Bootstrap frequency |
|---|---|---|---|---|---|---|
| `ctgan` | 20 | 0.0937 ± 0.0127 | 0.5094 ± 0.1167 | 0.6370 ± 0.0156 | yes | 0.81 |
| `gaussian_copula` | 20 | 0.0165 ± 0.0009 | 0.5932 ± 0.1639 | 0.6448 ± 0.0188 | yes | 0.93 |
| `gaussian_copula_shrink025` | 20 | 0.0165 ± 0.0010 | 0.6586 ± 0.1768 | 0.6511 ± 0.0197 | yes | 0.94 |
| `independent_marginals` | 20 | 0.0162 ± 0.0007 | 0.4861 ± 0.1684 | 0.6380 ± 0.0156 | yes | 0.97 |
| `tvae` | 20 | 0.1063 ± 0.0039 | 0.7042 ± 0.0949 | 0.6798 ± 0.0175 | yes | 0.84 |

P(row arm dominates column arm) on the main axes:

| | `ctgan` | `gaussian_copula` | `gaussian_copula_shrink025` | `independent_marginals` | `tvae` |
|---|---|---|---|---|---|
| `ctgan` | - | 0.00 | 0.00 | 0.00 | 0.00 |
| `gaussian_copula` | 0.07 | - | 0.06 | 0.03 | 0.00 |
| `gaussian_copula_shrink025` | 0.01 | 0.05 | - | 0.00 | 0.16 |
| `independent_marginals` | 0.14 | 0.01 | 0.00 | - | 0.00 |
| `tvae` | 0.00 | 0.00 | 0.00 | 0.00 | - |

Sensitivity: bootstrap frequency of being on the frontier under other axis choices (1,000 resamples each, so the `main` column differs slightly from the table above).

| Arm | main | + correlation axis | utility = LR only | utility = RF only | privacy = 4 numeric | privacy = Gower | privacy = ICD-9 codes | no utility axis |
|---|---|---|---|---|---|---|---|---|
| `ctgan` | 0.81 | 0.80 | 0.66 | 0.92 | 0.61 | 0.94 | 0.81 | 0.57 |
| `gaussian_copula` | 0.92 | 0.95 | 0.90 | 0.91 | 0.77 | 0.97 | 0.92 | 0.29 |
| `gaussian_copula_shrink025` | 0.95 | 1.00 | 0.88 | 0.97 | 0.94 | 0.93 | 0.94 | 0.18 |
| `independent_marginals` | 0.97 | 0.97 | 0.98 | 0.97 | 0.88 | 1.00 | 0.98 | 0.97 |
| `tvae` | 0.86 | 0.83 | 0.72 | 0.87 | 0.98 | 0.85 | 0.83 | 0.00 |

Privacy ordering on each attack (mean AUROC, higher means more leakage):

| Attack | Order, most to least leaky |
|---|---|
| 4 numeric columns | `gaussian_copula_shrink025` (0.518), `gaussian_copula` (0.515), `ctgan` (0.507), `independent_marginals` (0.507), `tvae` (0.503) |
| Gower | `tvae` (0.649), `gaussian_copula_shrink025` (0.617), `gaussian_copula` (0.585), `independent_marginals` (0.551), `ctgan` (0.541) |
| ICD-9 codes | `tvae` (0.680), `gaussian_copula_shrink025` (0.651), `gaussian_copula` (0.645), `independent_marginals` (0.638), `ctgan` (0.637) |
| Worst case | `tvae` (0.680), `gaussian_copula_shrink025` (0.651), `gaussian_copula` (0.645), `independent_marginals` (0.638), `ctgan` (0.637) |

| Reading | Evidence |
|---|---|
| No arm dominates, so the frontier does not rank generators | All five are on it, with bootstrap frequencies of 0.81 to 0.97 and no pairwise dominance probability above 0.16 |
| CTGAN's place is fragile | Independent marginals dominate it in 14% of resamples, and CTGAN's edges over that floor are 0.023 of utility (not significant) and 0.0007 of worst-case AUROC |
| TVAE is on the frontier only because of utility | Without the utility axis its frequency is 0.00, since every other arm beats it on fidelity and privacy; and its utility is the copied signal described in the full evaluation |
| The worst-case privacy axis is needed | With the 4-column attack as the privacy axis TVAE looks safest and its frontier frequency rises to 0.98 |
| The positive control is detected | TVAE ranks most leaky on Gower, code-set and worst-case attacks, and least leaky on the 4-column attack |
| Every other arm beats TVAE on fidelity and on privacy | TVAE keeps its frontier place only through utility; the closest utility competitor is the copula at 0.25 shrinkage (0.659 vs 0.704, not significant, p = 0.25), and its P(dominates TVAE) is 0.16 |

What was validated and what was not:

| Check | Result |
|---|---|
| Dominance logic on known cases | passes, listed in [`pareto_result.md`](pareto_result.md) |
| Frontier under eight axis choices | membership changes with the axes, shown above |
| Privacy axis catches a real memorizer | yes, TVAE, on three of four attacks |
| Frontier against a genuinely privacy-preserving generator | not possible yet, none exists |
| Frontier on another dataset or patient sample | not tested |

---

## Raw evidence

```
$ python -m evaluation.pareto
arm                          seeds       fidelity JS      utility TSTR   privacy worst MIA  frontier  boot freq
ctgan                           20 0.0937 +/- 0.0127 0.5094 +/- 0.1167   0.6370 +/- 0.0156       yes       0.81
gaussian_copula                 20 0.0165 +/- 0.0009 0.5932 +/- 0.1639   0.6448 +/- 0.0188       yes       0.93
gaussian_copula_shrink025       20 0.0165 +/- 0.0010 0.6586 +/- 0.1768   0.6511 +/- 0.0197       yes       0.94
independent_marginals           20 0.0162 +/- 0.0007 0.4861 +/- 0.1684   0.6380 +/- 0.0156       yes       0.97
tvae                            20 0.1063 +/- 0.0039 0.7042 +/- 0.0949   0.6798 +/- 0.0175       yes       0.84

P(row arm dominates column arm) on the main axes, bootstrap over seeds
                                         ctgan   gaussian_copula gaussian_copula_s independent_margi              tvae
ctgan                                        -              0.00              0.00              0.00              0.00
gaussian_copula                           0.07                 -              0.06              0.03              0.00
gaussian_copula_shrink025                 0.01              0.05                 -              0.00              0.16
independent_marginals                     0.14              0.01              0.00                 -              0.00
tvae                                      0.00              0.00              0.00              0.00                 -

Sensitivity: bootstrap frequency of being on the frontier under other axis choices
arm                                          main   + correlation axis    utility = LR only    utility = RF only  privacy = 4 numeric      privacy = Gower  privacy = ICD-9 cod      no utility axis
ctgan                                        0.81                 0.80                 0.66                 0.92                 0.61                 0.94                 0.81                 0.57
gaussian_copula                              0.92                 0.95                 0.90                 0.91                 0.77                 0.97                 0.92                 0.29
gaussian_copula_shrink025                    0.95                 1.00                 0.88                 0.97                 0.94                 0.93                 0.94                 0.18
independent_marginals                        0.97                 0.97                 0.98                 0.97                 0.88                 1.00                 0.98                 0.97
tvae                                         0.86                 0.83                 0.72                 0.87                 0.98                 0.85                 0.83                 0.00
```

---

## Contrast with the two-baseline frontier

[`pareto_result.md`](pareto_result.md) had two generators, both on the frontier, and concluded the baselines could not be ordered. Five arms give the same answer, but the sensitivity analysis adds two things the two-arm version could not show: which arms owe their place to a single axis (TVAE to utility), and that a weak privacy attack would have made the memorizing generator look best.
