# Attribute Inference on Covered Attributes Result — no membership-specific leak found, and the attack can only see memorization here (2026-09-19)

Raw evidence for the attribute-inference attack rerun on three attributes that both splits cover, replacing the ethnicity run in [`attribute_inference_result.md`](attribute_inference_result.md). Reproduce with `python -m evaluation.attribute_inference` (ceiling control), `python -m evaluation.eval_runner --generator <name> --seed <n>` for each seed, then `python -m evaluation.summarize_results`.

---

## Method (honest framing)

The attacker is a 200-tree random forest trained on one synthetic dataset to predict a target attribute from every other column, then scored on two real sets: the 94 train rows the generator was fit on (members) and the 35 holdout rows (non-members). Three targets have full class coverage in both splits: `gender` (47 F / 47 M in train), `first_careunit` (5 classes) and `age_bucket` (<65, 65-79, 80+, edges chosen before looking at results; `age` and `age_89_plus` are dropped from the predictors for that target). `admission_type` was left out (91% one class) and mortality is covered by the utility metric.

The score is balanced accuracy minus chance (1 / number of classes present), so a class mix that differs between train and holdout cannot manufacture an uplift the way plain accuracy did for ethnicity. Two quantities are reported: **member uplift** (how far above chance the attacker is on training records) and **member gap** (member uplift minus non-member uplift), which is the part that is specific to having been in the training set. Each generator is run over 20 seeds (42 to 61).

What this does not show:

- **A null result here is weak evidence.** Real data barely supports inferring these attributes on unseen records (see the control below: real train → holdout gives uplift −0.120, 0.032 and 0.096), so an attacker has little to find even without any leak. The attack detects memorization (the ceiling control) and little else on this dataset.
- **The member gap has a built-in bias on `gender`.** `independent_marginals` breaks every cross-column relationship, so it cannot support attribute inference, yet its `gender` gap is 0.062. That comes from the non-member set (12 F / 23 M) being unlike the member set (47 / 47). Read each generator's gap against `independent_marginals`, not against zero.
- **The p-values below are uncorrected across 12 tests** and only reflect generator seeds, not a different sample of patients.
- **Only two baselines were attacked.** Neither models the joint distribution well (Track 1 reports Ledoit-Wolf shrinks the copula's latent correlation by 0.668), so there is little dependence for an attacker to exploit.

**Honest phrasing for the report: "on attributes with class coverage in both splits, an attacker trained on either baseline gains 0.00 to 0.04 balanced accuracy over chance on training records and shows no membership-specific gap beyond the no-dependence control; this attack is only sensitive to memorization on a dataset this small, where even real data supports little attribute inference."**

---

## Results

### Baselines, mean ± sd over 20 seeds

| Target | Generator | Member uplift | p vs 0 | Member gap | p vs 0 |
|---|---|---|---|---|---|
| `gender` | `gaussian_copula` | 0.042 ± 0.050 | 0.002 | 0.056 ± 0.114 | 0.041 |
| `gender` | `independent_marginals` | 0.027 ± 0.051 | 0.030 | 0.062 ± 0.092 | 0.007 |
| `first_careunit` | `gaussian_copula` | 0.003 ± 0.014 | 0.347 | 0.009 ± 0.019 | 0.049 |
| `first_careunit` | `independent_marginals` | −0.004 ± 0.007 | 0.009 | −0.003 ± 0.016 | 0.420 |
| `age_bucket` | `gaussian_copula` | 0.044 ± 0.049 | 0.001 | −0.001 ± 0.090 | 0.960 |
| `age_bucket` | `independent_marginals` | 0.006 ± 0.047 | 0.601 | −0.021 ± 0.083 | 0.270 |

### Ceiling control: attacker trained on an exact copy of the members

| Target | Members (bal. acc.) | Non-members (bal. acc.) | Member uplift | Non-member uplift | Member gap |
|---|---|---|---|---|---|
| `gender` | 1.000 | 0.380 | 0.500 | −0.120 | 0.620 |
| `first_careunit` | 1.000 | 0.232 | 0.800 | 0.032 | 0.768 |
| `age_bucket` | 1.000 | 0.429 | 0.667 | 0.096 | 0.571 |

| Reading | Evidence |
|---|---|
| The attack detects memorization | The exact-copy control gives member gaps of 0.57 to 0.77 |
| Neither baseline memorizes attributes | Copula gaps 0.056, 0.009 and −0.001 against 0.62, 0.77 and 0.57 for the ceiling |
| The `gender` gap is a set-composition effect | `independent_marginals` has no dependence to exploit yet shows 0.062, the same as the copula's 0.056 |
| The copula keeps a small population-level age signal | Member uplift 0.044 vs 0.006 for `independent_marginals` (Welch p = 0.017), with a gap of −0.001, so it applies equally to unseen records and is not a membership leak |
| Most other p < 0.05 entries are tiny | All effects are under 0.07 against seed sds of 0.01 to 0.11, from 12 uncorrected tests |

---

## Raw evidence

```
$ python -m evaluation.attribute_inference
Ceiling control: attacker trained on an exact copy of the members
  target             members   non-mem  uplift(m)  uplift(n)      gap
  gender               1.000     0.380      0.500     -0.120    0.620
  first_careunit       1.000     0.232      0.800      0.032    0.768
  age_bucket           1.000     0.429      0.667      0.096    0.571
```

```
$ python -m evaluation.summarize_results   (attribute rows only)
gaussian_copula  (n_seeds=20)
  attr_gender_uplift_members   0.0415 +/- 0.0501
  attr_gender_gap              0.0561 +/- 0.1143
  attr_first_careunit_uplift_members 0.0030 +/- 0.0141
  attr_first_careunit_gap      0.0087 +/- 0.0186
  attr_age_bucket_uplift_members 0.0435 +/- 0.0492
  attr_age_bucket_gap          -0.0010 +/- 0.0904
independent_marginals  (n_seeds=20)
  attr_gender_uplift_members   0.0266 +/- 0.0507
  attr_gender_gap              0.0617 +/- 0.0916
  attr_first_careunit_uplift_members -0.0044 +/- 0.0067
  attr_first_careunit_gap      -0.0029 +/- 0.0159
  attr_age_bucket_uplift_members 0.0056 +/- 0.0466
  attr_age_bucket_gap          -0.0211 +/- 0.0832
```

```
one-sample t-tests against 0 (20 seeds), and copula vs independent on member uplift
gender          gaussian_copula        0.0415  p=0.002   gap 0.0561  p=0.041
gender          independent_marginals  0.0266  p=0.030   gap 0.0617  p=0.007
first_careunit  gaussian_copula        0.0030  p=0.347   gap 0.0087  p=0.049
first_careunit  independent_marginals -0.0044  p=0.009   gap -0.0029 p=0.420
age_bucket      gaussian_copula        0.0435  p=0.001   gap -0.0010 p=0.960
age_bucket      independent_marginals  0.0056  p=0.601   gap -0.0211 p=0.270
copula vs independent member uplift: gender p=0.356, first_careunit p=0.043, age_bucket p=0.017
```

---

## Contrast with the ethnicity run

[`attribute_inference_result.md`](attribute_inference_result.md) reported 0.0000 uplift because the attacker never saw the Puerto Rican class, and it scored holdout rows only, so it measured general inference and not membership leakage. This run picks attributes both splits cover, scores members and non-members separately, and uses balanced accuracy. It still finds nothing, but it now has a ceiling control showing the attack can detect memorization, and a no-dependence generator to read the gap against.
