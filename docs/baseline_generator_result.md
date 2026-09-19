# Statistical Baseline Result — first synthetic data, run through the Stage 2 contract and Track 2's metrics (2026-09-18)

Raw evidence that the generation stage runs end to end and that its output feeds Track 2's code with no changes. Reproduce with the commands in [`A1_generative_modeling.md`](A1_generative_modeling.md).

---

## Method (honest framing)

Both generators fit on the 94 train rows only. Fidelity and utility come from Track 2's own `fidelity_metrics.run_fidelity_report` and `utility_eval.utility_gap_report`, with every CSV read through plain `pd.read_csv`, exactly as Track 2's scripts read it. This is the first real synthetic data in the project. Since it's a baseline, the question it answers is whether the pipeline works and where the floor sits, not which generator wins.

---

## Results

### Contract

| Check | Result |
|---|---|
| `gaussian_copula_seed42.csv` | PASS, 94 rows |
| `independent_marginals_seed42.csv` | PASS, 94 rows |
| Same seed run twice | identical SHA-256 |
| Real train through encode → decode | PASS |
| Real holdout relabelled as synthetic | FAIL as intended: ID collisions, holdout-only ethnicity, 18 unseen primary codes, 30 rows of unseen codes |

### Fidelity, seed 42

| Arm | vs train: mean JSD | vs train: corr. diff | vs train: KS pass | vs holdout: mean JSD | vs holdout: corr. diff |
|---|---|---|---|---|---|
| Real train (Track 2's stand-in, the real-vs-real floor) | 0.000 | 0.000 | 1.00 | 0.100 | 0.203 |
| `independent_marginals` | 0.017 | 0.160 | 1.00 | 0.121 | 0.227 |
| `gaussian_copula` | 0.016 | 0.139 | 1.00 | 0.120 | 0.215 |

Against train, both reproduce the marginals almost exactly, which is by construction since both sample empirical marginals. Correlation is what separates them. The copula recovers some dependence (0.139 vs 0.160) but not much, because Ledoit-Wolf shrinks the latent correlation by 0.668. Against the holdout, both land within about 0.02 of the real-vs-real floor, so holdout fidelity on this dataset mostly measures the 94/35 sampling gap.

### Utility, TSTR over 20 seeds

| Arm | LR mean ± sd | LR range | RF mean ± sd | RF range |
|---|---|---|---|---|
| `independent_marginals` | 0.468 ± 0.196 | 0.07 – 0.72 | 0.537 ± 0.181 | 0.25 – 0.77 |
| `gaussian_copula` | 0.559 ± 0.239 | 0.14 – 0.90 | 0.555 ± 0.172 | 0.29 – 0.90 |
| TRTR ceiling (5-fold CV, real train) | 0.578 | | 0.737 | |

`independent_marginals` has zero feature-label dependence, so its TSTR should sit at chance, and the 20-seed means (0.47 and 0.54) show the harness scores it that way. Seed 42 alone gave 0.713 / 0.784, which is above the TRTR ceiling. With a spread of about 0.2 between seeds, the copula's lead over the floor sits inside the noise.

The cause is the holdout's composition. All 6 in-hospital deaths are among the 20 non-Puerto-Rican holdout admissions, and the 15 Puerto Rican admissions have none. The utility metric is effectively scored on 20 rows with 6 positives.

---

## Caveats on the metrics (raised with Track 2)

1. **Binary columns always score JSD 0.** `hospital_expire_flag` and `readmit_30d` are in `NUMERIC_COLS`, so they go through 10-quantile binning. With only the values {0, 1}, the bin edges collapse to [0, 1], which is a single bin, so JSD is 0 whatever the positive rate. Train mortality 36.2% vs holdout 17.1% scores 0.0000 on that path and 0.0340 on the categorical path. The note in [`fidelity_result.md`](fidelity_result.md) attributing the 0.0000 to similar positive rates doesn't hold. `age_89_plus` is in neither column list, so it isn't scored at all.
2. **The correlation threshold is below the noise floor.** Real train vs real holdout scores 0.203, already past the 0.20 "acceptable" cutoff, so no generator can pass correlation against the holdout.
3. **Single-seed TSTR can't be interpreted** on this holdout, as shown above. See ADR-012.

---

## Raw evidence

```
$ python -m generators.generate --generator gaussian_copula --seed 42
PASS  wrote output/synthetic/gaussian_copula_seed42.csv and gaussian_copula_seed42.manifest.json
$ python -m generators.generate --generator independent_marginals --seed 42
PASS  wrote output/synthetic/independent_marginals_seed42.csv and independent_marginals_seed42.manifest.json
$ python -m generators.validate output/synthetic/gaussian_copula_seed42.csv
PASS  output/synthetic/gaussian_copula_seed42.csv  (94 rows)
```

```
arm                              | vs TRAIN: meanJSD corrDiff KSpass | vs HOLDOUT: meanJSD corrDiff | TSTR LR / RF
real train (Track 2 stand-in)    |   0.000   0.000   1.00  |    0.100   0.203  | 0.489 / 0.888
independent_marginals            |   0.017   0.160   1.00  |    0.121   0.227  | 0.713 / 0.784
gaussian_copula                  |   0.016   0.139   1.00  |    0.120   0.215  | 0.356 / 0.724
TRTR ceiling (5-fold CV on real train): {'logistic_regression': 0.578, 'random_forest': 0.737}

independent_marginals  TSTR over 20 seeds | LR mean=0.468 sd=0.196 [0.07,0.72] | RF mean=0.537 sd=0.181 [0.25,0.77]
gaussian_copula        TSTR over 20 seeds | LR mean=0.559 sd=0.239 [0.14,0.90] | RF mean=0.555 sd=0.172 [0.29,0.90]

hospital_expire_flag: positive rate train=0.362 holdout=0.171 | continuous-path JSD=0.0000 | categorical-path JSD=0.0340
readmit_30d: positive rate train=0.096 holdout=0.057 | continuous-path JSD=0.0000 | categorical-path JSD=0.0038
holdout mortality: Puerto Rican rows 0/15 | others 6/20
```
