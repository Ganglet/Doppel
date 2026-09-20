# Initial Sweep Result — memorization vs fidelity for every generator config, inside train only (2026-09-19, regenerated 2026-09-20)

Raw evidence for the Phase 2 model-selection decision (ADR-024). Reproduce with `python -m generators.sweep --seeds 0 1 2` from the repo root (1,440 s on 6 workers).

> **Regenerated 2026-09-20.** Two changes since the first run: the copula samples through Cholesky (P-013), so its rows are new draws of the same distribution, and Track 2's fidelity metric now scores binary columns (P-007), which shifts every mean JSD slightly. `independent_marginals` and the CTGAN/TVAE rows come out identical apart from that metric change. No conclusion moved.

---

## Method (honest framing)

11 configs × 3 seeds × 5 patient folds = 165 fits, all completed. Each fit uses 4/5 of train (74–77 rows). Fidelity is Track 2's `run_fidelity_report` against those fit rows, and memorization is DCR against the unseen fifth (ADR-021). The holdout is never read.

These are **selection numbers, not benchmark numbers.** Fidelity against the rows a model was fitted on is in-sample by design, and it rewards copying. That's why it's only read alongside DCR. The holdout comparison is Phase 3. Selection guard: a config counts only if `dcr_ratio ≥ 0.95` and `near_copy_rate ≤ 0.10`. The 0.10 cutoff is twice what real unseen rows score.

---

## Results

Mean ± sd over 3 seeds, with each seed pooled over 5 folds.

| Generator | Config | DCR ratio | Near-copy rate | Mean JSD | Corr. diff | Guard |
|---|---|---|---|---|---|---|
| `independent_marginals` | (floor) | 1.099 ± 0.009 | 0.005 ± 0.005 | 0.020 ± 0.001 | 0.175 ± 0.001 | pass |
| `gaussian_copula` | Ledoit-Wolf | 1.073 ± 0.007 | 0.007 ± 0.002 | 0.020 ± 0.001 | 0.148 ± 0.001 | pass |
| `gaussian_copula` | λ = 0.9 | 1.090 ± 0.007 | 0.004 ± 0.002 | 0.020 ± 0.001 | 0.166 ± 0.001 | pass |
| `gaussian_copula` | λ = 0.5 | 1.059 ± 0.003 | 0.015 ± 0.004 | 0.020 ± 0.001 | 0.135 ± 0.000 | pass |
| `gaussian_copula` | **λ = 0.25** | 1.037 ± 0.014 | 0.021 ± 0.007 | 0.020 ± 0.001 | **0.119 ± 0.002** | pass |
| `ctgan` | 300 epochs | 1.175 ± 0.011 | 0.001 ± 0.002 | 0.103 ± 0.007 | 0.177 ± 0.001 | pass, below floor |
| `ctgan` | 1000 epochs | 1.209 ± 0.021 | 0.000 ± 0.000 | 0.133 ± 0.006 | 0.178 ± 0.001 | pass, below floor |
| `ctgan` | 3000 epochs | 1.281 ± 0.022 | 0.000 ± 0.000 | 0.139 ± 0.005 | 0.180 ± 0.002 | pass, below floor |
| `tvae` | 300 epochs | 0.719 ± 0.009 | 0.519 ± 0.039 | 0.117 ± 0.001 | 0.134 ± 0.002 | **fail** |
| `tvae` | 1000 epochs | 0.661 ± 0.007 | 0.661 ± 0.016 | 0.238 ± 0.012 | 0.122 ± 0.002 | **fail** |
| `tvae` | 3000 epochs | 0.640 ± 0.003 | 0.708 ± 0.013 | 0.190 ± 0.008 | 0.117 ± 0.001 | **fail** |

**Gaussian copula.** Shrinkage is a clean, monotonic trade-off. Less shrinkage preserves more correlation and brings rows closer to real ones, but it never reaches copying: near-copy stays at 0.021 even at λ = 0.25, below the 0.059 that real unseen rows score. Marginals are exact at every setting, by construction.

**CTGAN** copies nothing, but it's below the independent-marginals floor on both fidelity metrics. Its marginals are 5–7× worse (JSD 0.103–0.139 vs 0.020), and its correlation difference (0.177–0.180) matches the floor's 0.175, so it has learned no dependence. More training makes every metric worse. "Doesn't memorize" here means "hasn't learned the data", not "is private".

**TVAE** memorizes at every setting. Between 52% and 71% of its rows are near-copies, where 5% is what unseen real rows score, and the rate rises with training. Its correlation difference is the best of any generator (0.117), but that comes from copying, which is exactly the case the guard exists to catch.

---

## Failure modes, checked rather than assumed

Full train, seed 42, 300 epochs, scored with Track 2's per-column JSD:

| | CTGAN | TVAE | Real train |
|---|---|---|---|
| Worst columns | continuous: `lab_50931_mean` 0.27, `lab_51279_abnormal_frac` 0.24, `los_icu_days` 0.22 | `icd9_primary` 0.36, `n_diagnoses` 0.31, lab abnormal fractions 0.20–0.26 | |
| Distinct `icd9_primary` codes | 47 | **20** | 65 |
| Share of the most common primary code | 0.05 | **0.17** | |
| Distinct rows on 6 key discrete fields | 91 / 94 | **43 / 94** | |
| Rows matching a real row on those 6 fields | 0.07 | **0.34** | |
| Median hospital stay (days) | **11.9** | 7.1 | 6.7 |
| In-hospital mortality | 0.29 | 0.24 | 0.36 |

- **CTGAN** handles the categorical columns reasonably. Its failure is in the continuous ones, with the hospital-stay median nearly doubled. It fits a mixture of up to 10 modes per continuous column on about 75 values per column, and trains adversarially for a few hundred steps. Neither has enough data at this n.
- **TVAE** collapses onto a subset of patients. It uses 20 of 65 primary codes, and a third of its rows reproduce a real patient's key fields. That explains both the near-copies and the poor marginals: it copies some patients repeatedly and never generates the rest.

---

## Raw evidence

```
$ python -m generators.sweep --seeds 0 1 2
165 tasks on 6 workers
...
            generator              params  dcr_ratio_mean  dcr_ratio_std  near_copy_rate_mean  near_copy_rate_std  mean_js_mean  mean_js_std  corr_diff_mean  corr_diff_std  seeds
                ctgan    {"epochs": 1000}           1.209          0.021                0.000               0.000         0.133        0.006           0.178          0.001      3
                ctgan    {"epochs": 3000}           1.281          0.022                0.000               0.000         0.139        0.005           0.180          0.002      3
                ctgan     {"epochs": 300}           1.175          0.011                0.001               0.002         0.103        0.007           0.177          0.001      3
      gaussian_copula {"shrinkage": 0.25}           1.037          0.014                0.021               0.007         0.020        0.001           0.119          0.002      3
      gaussian_copula  {"shrinkage": 0.5}           1.059          0.003                0.015               0.004         0.020        0.001           0.135          0.000      3
      gaussian_copula  {"shrinkage": 0.9}           1.090          0.007                0.004               0.002         0.020        0.001           0.166          0.001      3
      gaussian_copula                  {}           1.073          0.007                0.007               0.002         0.020        0.001           0.148          0.001      3
independent_marginals                  {}           1.099          0.009                0.005               0.005         0.020        0.001           0.175          0.001      3
                 tvae    {"epochs": 1000}           0.661          0.007                0.661               0.016         0.238        0.012           0.122          0.002      3
                 tvae    {"epochs": 3000}           0.640          0.003                0.708               0.013         0.190        0.008           0.117          0.001      3
                 tvae     {"epochs": 300}           0.719          0.009                0.519               0.039         0.117        0.001           0.134          0.002      3

wrote output/sweeps/sweep_20260919T213256Z.csv and _summary.csv  (1440s)
```

DCR calibration, fold 0 (from ADR-021): real unseen rows `dcr_ratio` 1.000 / `near_copy_rate` 0.059, exact copies 0.000 / 1.000.
