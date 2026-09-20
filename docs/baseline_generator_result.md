# Statistical Baseline Result — first synthetic data, run through the Stage 2 contract and Track 2's metrics (2026-09-18, regenerated 2026-09-20)

Raw evidence that the generation stage runs end to end and that its output feeds Track 2's code with no changes. Reproduce with the commands in [`A1_generative_modeling.md`](A1_generative_modeling.md).

> **Regenerated 2026-09-20.** The copula's sampler changed from `eigh` to Cholesky (P-013), so every `gaussian_copula` number below comes from new draws of the same distribution. The old sampler gave a different seed-42 file under each numpy build. All numbers are now computed on the team environment (Python 3.11, root `requirements.txt`) with Track 2's current `evaluation` package, which scores 52 columns instead of 49 after the binary-column fix (P-007). `independent_marginals` came out identical to the last digit, as expected.

---

## Method (honest framing)

Both generators fit on the 94 train rows only. Fidelity and utility come from Track 2's own `evaluation.fidelity_metrics.run_fidelity_report` and `evaluation.utility_eval.utility_gap_report`, with every CSV read through plain `pd.read_csv`, exactly as Track 2's scripts read it. This is the first real synthetic data in the project. Since it's a baseline, the question it answers is whether the pipeline works and where the floor sits, not which generator wins.

---

## Results

### Contract

| Check | Result |
|---|---|
| `gaussian_copula_seed42.csv` | PASS, 94 rows |
| `independent_marginals_seed42.csv` | PASS, 94 rows |
| Same seed run twice | identical SHA-256 |
| Same seed on Python 3.11 / numpy 2.4.6 and Python 3.12 / numpy 2.5.3 | identical SHA-256 (all four generators, P-013) |
| Real train through encode → decode | PASS |
| Real holdout relabelled as synthetic | FAIL as intended: ID collisions, holdout-only ethnicity, 18 unseen primary codes, 30 rows of unseen codes |

### Fidelity, seed 42

| Arm | vs train: mean JSD | vs train: corr. diff | vs train: KS pass | vs holdout: mean JSD | vs holdout: corr. diff |
|---|---|---|---|---|---|
| Real train (Track 2's stand-in, the real-vs-real floor) | 0.000 | 0.000 | 1.00 | 0.099 | 0.203 |
| `independent_marginals` | 0.017 | 0.160 | 1.00 | 0.119 | 0.227 |
| `gaussian_copula` | 0.016 | 0.132 | 1.00 | 0.117 | 0.214 |

Against train, both reproduce the marginals almost exactly, which is by construction since both sample empirical marginals. Correlation is what separates them. The copula recovers some dependence (0.132 vs 0.160) but not much, because Ledoit-Wolf shrinks the latent correlation by 0.668. Against the holdout, both land within about 0.02 of the real-vs-real floor, so holdout fidelity on this dataset mostly measures the 94/35 sampling gap.

### Utility, TSTR over 20 seeds

| Arm | LR mean ± sd | LR range | RF mean ± sd | RF range |
|---|---|---|---|---|
| `independent_marginals` | 0.468 ± 0.196 | 0.07 – 0.72 | 0.537 ± 0.181 | 0.25 – 0.77 |
| `gaussian_copula` | 0.547 ± 0.175 | 0.30 – 0.89 | 0.589 ± 0.145 | 0.40 – 0.91 |
| TRTR ceiling (5-fold CV, real train) | 0.578 | | 0.737 | |

`independent_marginals` has zero feature-label dependence, so its TSTR should sit at chance, and the 20-seed means (0.47 and 0.54) show the harness scores it that way. Seed 42 alone gave 0.713 / 0.784, which is above the TRTR ceiling. With a spread of about 0.2 between seeds, the copula's lead over the floor sits inside the noise.

The cause is the holdout's composition. All 6 in-hospital deaths are among the 20 non-Puerto-Rican holdout admissions, and the 15 Puerto Rican admissions have none. The utility metric is effectively scored on 20 rows with 6 positives.

The eigh sampler made the same point in another way. The copula's seed-42 TSTR (LR) came out 0.356, 0.770 or 0.931 depending on the numpy build (P-008, P-009). One seed's utility number can swing by more than half an AUROC point without any change to the model.

---

## Caveats on the metrics (raised with Track 2, now resolved)

1. **Binary columns always scored JSD 0.** They went through 10-quantile binning, which collapses {0, 1} into one bin. Fixed by Track 2 (P-007): they now score 0.0340, 0.0038 and 0.0112 on train vs holdout, and `age_89_plus` is included.
2. **The correlation threshold sat below the noise floor** (real-vs-real 0.203 vs the 0.20 cutoff). Track 2 replaced it with noise-floor references (ADR-015).
3. **Single-seed TSTR can't be interpreted** on this holdout. Adopted by Track 2: utility is now reported as mean ± sd over 20 seeds (ADR-015). See also ADR-012.

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
numpy 2.4.6
arm                     | vsTRAIN meanJSD corr  KS  | vsHOLD meanJSD corr  | seed-42 TSTR LR / RF | cols
real train (stand-in)   |  0.000  0.000 1.00 |  0.099  0.203 | 0.489 / 0.888        | 52
independent_marginals   |  0.017  0.160 1.00 |  0.119  0.227 | 0.713 / 0.784        | 52
gaussian_copula         |  0.016  0.132 1.00 |  0.117  0.214 | 0.695 / 0.819        | 52
TRTR ceiling: {'logistic_regression': 0.578, 'random_forest': 0.737}

independent_marginals  TSTR 20 seeds | LR 0.468 ± 0.196 [0.07,0.72] | RF 0.537 ± 0.181 [0.25,0.77]
gaussian_copula        TSTR 20 seeds | LR 0.547 ± 0.175 [0.30,0.89] | RF 0.589 ± 0.145 [0.40,0.91]

binary JSD now (train vs holdout) hospital_expire_flag: 0.0340
binary JSD now (train vs holdout) readmit_30d: 0.0038
binary JSD now (train vs holdout) age_89_plus: 0.0112
holdout mortality: Puerto Rican rows 0/15 | others 6/20
```
