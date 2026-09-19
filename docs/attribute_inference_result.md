# Attribute Inference Result — attack ran, and the zero-uplift score traces to a data artifact, not privacy protection (2026-09-17)

Raw evidence for what `attribute_inference.py` actually measured, and why the headline number (0.0000 uplift) is not a valid privacy claim on its own. Reproduce with `python attribute_inference.py` from the repo root.

> **Stand-in run (Phase 1).** This measured real train against real holdout, not a generator. The same metric on real synthetic data is in [`baseline_evaluation_result.md`](baseline_evaluation_result.md) and [`B2_eval_runner.md`](B2_eval_runner.md).

> **Superseded:** the ethnicity target is not scored any more. See [`attribute_targets_result.md`](attribute_targets_result.md).

---

## Method (honest framing)

An attacker (Random Forest) is trained on the stand-in "synthetic" data (real `train` split, per ADR-005) to predict `ethnicity` from every other column, then scored on the real `holdout` split. Accuracy is compared against the base rate (always guessing the majority class).

The result below (0.0000 uplift) looks like a privacy success — the attacker did no better than guessing. **It is not one.** Investigation traced it to the training data itself: `HISPANIC/LATINO - PUERTO RICAN` is 15 of 35 holdout admissions (43%) but 0 of 94 train admissions (see [`problems_and_decisions.md`](problems_and_decisions.md) P-003). The attacker predicted `WHITE` for all 35 holdout rows because it had never seen the other class during training — not because it correctly reasoned that the other features carry no signal about ethnicity. **Honest phrasing for the report: "the attribute-inference attack implementation runs correctly, but this particular result is invalidated by a class-coverage gap between train and holdout on a 100-patient sample; a meaningful uplift measurement requires either a larger population or a stratified split that guarantees class coverage."**

---

## Results

| Metric | Value |
|---|---|
| Target attribute | `ethnicity` |
| Attacker accuracy | 0.5143 |
| Base-rate accuracy (majority class) | 0.5143 |
| Uplift (attacker − base rate) | 0.0000 |

| Split | `WHITE` | `HISPANIC/LATINO - PUERTO RICAN` | `UNKNOWN/NOT SPECIFIED` | `OTHER` | `BLACK/AFRICAN AMERICAN` | `ASIAN` |
|---|---|---|---|---|---|---|
| train (n=94) | 68 | 0 | 9 | 8 | 7 | 2 |
| holdout (n=35) | 18 | 15 | 2 | 0 | 0 | 0 |

---

## Raw evidence

```
$ python attribute_inference.py
Target attribute: ethnicity
Attacker accuracy: 0.5143
Base rate accuracy (majority class): 0.5143
Uplift (attacker - base rate): 0.0000
```

```
$ python -c "
import pandas as pd
df = pd.read_csv('output/mimic_demo_clean.csv')
print(df[df['split']=='train']['ethnicity'].value_counts())
print(df[df['split']=='holdout']['ethnicity'].value_counts())
"
ethnicity
WHITE                     68
UNKNOWN/NOT SPECIFIED      9
OTHER                      8
BLACK/AFRICAN AMERICAN     7
ASIAN                      2

ethnicity
WHITE                             18
HISPANIC/LATINO - PUERTO RICAN    15
UNKNOWN/NOT SPECIFIED              2
```

No predicted class other than `WHITE` appeared anywhere in the attacker's holdout predictions — confirmed directly, not inferred from the accuracy number alone.
