# Pareto Frontier Result — the two baselines cannot be ordered on fidelity, utility and privacy (2026-09-19)

Raw evidence that `evaluation/pareto.py` runs on the contract JSON and what it says about the two Track 1 baselines. Reproduce with `python -m evaluation.eval_runner --generator <name> --seed <n>` for seeds 42 to 61 for each generator, then `python -m evaluation.pareto`.

> **Superseded (2026-09-24):** this frontier covers two baselines. The five-arm frontier, with sensitivity checks, is in [`full_pareto_result.md`](full_pareto_result.md).

---

## Method (honest framing)

Each generator is reduced to three numbers per seed, then a generator is on the frontier if no other generator is at least as good on all three axes and strictly better on one.

| Axis | Definition | Better is |
|---|---|---|
| Fidelity | mean JS divergence vs real train, 52 columns | lower |
| Utility | mean of the logistic regression and random forest TSTR AUROC on `hospital_expire_flag` | higher |
| Privacy | `membership_worst_case`: the highest mean AUROC over the three realistic membership attacks (4 numeric columns, Gower over all columns, ICD-9 code sets) | lower |

Frontier membership is also bootstrapped over seeds (2,000 resamples), so a generator that leads by seed noise shows a low frequency, and the probability that one generator dominates another is reported.

What this does not show:

- **This is a frontier of two floors, not the project's result.** `gaussian_copula` is the statistical baseline and `independent_marginals` is a no-dependence control. CTGAN/TVAE and the diffusion model don't exist yet, so no line here speaks to the blueprint's real comparison. The evaluation has to be rerun when they land.
- **The axes are my choices.** Fidelity ignores correlation, which is the one fidelity metric that separates these two (0.1355 vs 0.1629). A fourth axis for it could change which generator is ahead.
- **The privacy axis is currently the ICD-9 code-set attack for both generators** (0.639 and 0.638), so it measures how rare codes are reproduced. A generator that suppresses rare codes would do well on it whatever else it does.
- **Utility is noise-dominated.** Its seed sd is 0.16 to 0.17 on a holdout with 6 positives.
- **Two points are not a curve.** With two generators the frontier can only be "both", "one", or a tie.
- **Bootstrap probabilities are over generator seeds on one dataset,** not over patients.

**Honest phrasing for the report: "on the two baselines no generator dominates the other on fidelity, utility and worst-case membership risk; the copula's only clear edge is utility, and both leak equally through ICD-9 codes."**

---

## Results

| Generator | Seeds | Fidelity (JS) | Utility (TSTR) | Privacy (worst MIA AUROC) | On frontier | Bootstrap frequency |
|---|---|---|---|---|---|---|
| `gaussian_copula` | 20 | 0.0189 ± 0.0013 | 0.6247 ± 0.1558 | 0.6387 ± 0.0157 | yes | 1.00 |
| `independent_marginals` | 20 | 0.0183 ± 0.0008 | 0.4861 ± 0.1684 | 0.6380 ± 0.0156 | yes | 0.99 |

| P(row dominates column) | `gaussian_copula` | `independent_marginals` |
|---|---|---|
| `gaussian_copula` | - | 0.01 |
| `independent_marginals` | 0.00 | - |

| Reading | Evidence |
|---|---|
| Neither generator dominates | Both are on the frontier, and dominance probabilities are 0.01 and 0.00 |
| The copula's edge is utility | 0.625 vs 0.486, about 0.14 higher (Welch p = 0.046 for LR and 0.009 for RF in [`baseline_evaluation_result.md`](baseline_evaluation_result.md), uncorrected) |
| Fidelity and privacy are ties | JS differs by 0.0006 (p = 0.12) and worst-case AUROC by 0.0007, both far inside seed sd |

---

## Raw evidence

```
$ python -m evaluation.pareto
generator                seeds       fidelity JS      utility TSTR   privacy worst MIA  frontier  boot freq
gaussian_copula             20 0.0189 +/- 0.0013 0.6247 +/- 0.1558   0.6387 +/- 0.0157       yes       1.00
independent_marginals       20 0.0183 +/- 0.0008 0.4861 +/- 0.1684   0.6380 +/- 0.0156       yes       0.99

P(row generator dominates column generator), bootstrap over seeds
                                 gaussian_copula   independent_marginals
gaussian_copula                                -                    0.01
independent_marginals                       0.00                       -
```

```
dominance logic checked on known cases (fidelity min, utility max, privacy min)
good dominates worse      : True (expect True)
worse dominates good      : False (expect False)
good dominates lowutil    : True (expect True: equal JS/MIA, higher utility)
good dominates identical  : False (expect False: needs one strictly better)
good vs mix (trade-off)   : False False (expect False False)
frontier of {good,worse,lowutil,mix}: ['good', 'mix'] (expect ['good','mix'])
```
