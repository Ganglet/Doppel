# Fidelity Metrics Result — JS divergence, correlation preservation, and KS checks run and validated (2026-09-17)

Raw evidence that `evaluation/fidelity_metrics.py` runs end-to-end and produces sane output. Reproduce with `python -m evaluation.fidelity_metrics` from the repo root.

---

## Method (honest framing)

This measures the real `train` split against the real `holdout` split of `output/mimic_demo_clean.csv` — **not** a generator's synthetic output against real data, because no generator exists yet (see [`B1_evaluation_pipeline.md`](B1_evaluation_pipeline.md), ADR-005). What was actually validated: the metric code runs without error on 49 real columns, produces JS divergence scores in the expected [0, 1] range, and the correlation-preservation and KS calculations don't crash on nulls or mixed types.

What this is *not* evidence of: fidelity of any synthetic data generator. The mean JS divergence reported below (0.1001) is real-vs-real sampling noise on a 94-row vs. 35-row split, not a "how good is CTGAN" number. **Honest phrasing for the report: "the fidelity metric implementation is validated and produces a real-vs-real noise floor of ~0.10 mean JS divergence on this dataset; generator fidelity has not yet been measured."**

---

## Results

| Metric | Value | Protocol threshold ([`eval_protocol.md`](../eval_protocol.md)) |
|---|---|---|
| Mean JS divergence (49 columns) | 0.1001 | ≤ 0.10 good, ≤ 0.20 acceptable |
| Correlation preservation (mean abs. diff) | 0.2025 | ≤ 0.10 good, ≤ 0.20 acceptable |
| KS test pass fraction (p ≥ 0.05) | 0.6522 | reported, not gated |

Highest-divergence columns (real-vs-real noise, not generator failure):

| Column | JS divergence |
|---|---|
| `icd9_primary` | 0.7291 |
| `ethnicity` | 0.3211 |
| `lab_51248_mean` | 0.2829 |
| `lab_51250_mean` | 0.2531 |

---

## Raw evidence

```
$ python -m evaluation.fidelity_metrics
Mean JS divergence: 0.1001
Correlation preservation (mean abs diff): 0.2025
KS test pass fraction (p >= 0.05): 0.6522

Per-column JS divergence:
  icd9_primary: 0.7291
  ethnicity: 0.3211
  lab_51248_mean: 0.2829
  lab_51250_mean: 0.2531
  lab_50970_mean: 0.1927
  age: 0.1683
  ...
  hospital_expire_flag: 0.0000
  readmit_30d: 0.0000
```

(`hospital_expire_flag` and `readmit_30d` show 0.0000 because both splits happen to share a similar positive rate — not because these columns are trivially "easy," just a real coincidence of this particular split.)

---

## Correction (2026-09-19)

The parenthetical above, that `hospital_expire_flag` and `readmit_30d` scored 0.0000 because both splits share a similar positive rate, is wrong. Track 1 found that the 10-quantile binning collapses a two-valued column to one bin, so those columns scored 0 whatever the rates were (train mortality 36.2%, holdout 17.1%). See P-007 in [`problems_and_decisions.md`](problems_and_decisions.md). After the fix the real-vs-real numbers are: mean JSD 0.0991 over 52 columns (was 0.1001 over 49), correlation diff 0.2025 and KS pass fraction 0.6522 (both unchanged). The two flags now score 0.0340 and 0.0038, and `age_89_plus` scores 0.0112.

