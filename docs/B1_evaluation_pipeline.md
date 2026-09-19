# Privacy & Utility Evaluation Pipeline

**Phase:** Phase 1 — Foundation & Design (Weeks 1–2), with the metric code written early against a stand-in dataset
**Owner:** Rayyan (Track 2 / Track B)
**Status:** Complete. The protocol and four metric modules were implemented and self-tested against a stand-in. Running them on real synthetic data, the result JSON, calibration and the Pareto module are in [`B2_eval_runner.md`](B2_eval_runner.md).

---

## Objective

Define one evaluation protocol — exact formulas and thresholds for fidelity, downstream utility, and privacy — and build the code to run it, so all three of Track 1's generator families get scored on identical terms instead of ad hoc, incomparable metrics. This exists because the blueprint's core claim is comparability, and comparability requires the protocol to be fixed and implemented before the generators it will score even exist.

---

## What was built

### Evaluation protocol
Full formulas and pass/fail thresholds for fidelity (JS divergence, correlation preservation, KS tests), utility (TRTR/TSTR AUROC), and privacy (membership + attribute inference) are in [`eval_protocol.md`](../eval_protocol.md). Downstream utility label was chosen there too: `hospital_expire_flag` over `readmit_30d`, based on holdout class counts (ADR-003).

### Four standalone metric modules

```
fidelity_metrics.py        JS divergence (categorical + binned continuous),
                            correlation preservation, KS dimension-wise checks
utility_eval.py             TRTR (5-fold CV on real train) vs TSTR
                            (train-on-synthetic, test-on-real holdout)
membership_inference.py     Shadow-model attack: nearest-neighbor distance
                            feature, leave-one-shadow-out attack evaluation
attribute_inference.py      Attacker trained on synthetic data predicts a
                            withheld attribute (ethnicity) from the rest
```

Each module runs standalone against `output/mimic_demo_clean.csv` and is importable by Track 4's aggregation stage once that exists.

### Stand-in testing strategy
None of these modules could be tested against real synthetic data (Track 1 hasn't started), so every module was built and validated by treating the real `train` split as a placeholder for synthetic data, scored against the real `holdout` split — same interface a real generator's output will use later. This is ADR-005, and it's why every number in the result docs below is explicitly scoped as "validates the code, not a generator."

### Membership-inference sanity check
Because a distance-based membership attack has no ground truth to check itself against without a real generator, `membership_inference.py` includes a built-in self-validation: it runs the attack against a deliberately memorizing stand-in generator (`noise_scale=0.0`, exact resampling) and a deliberately noisy one (`noise_scale=0.3`), and the attack AUROC should be — and is — higher for the memorizing one. See [`membership_inference_result.md`](membership_inference_result.md).

---

## Commands

```bash
# Setup
pip install pandas==2.3.3 numpy scikit-learn==1.8.0 scipy==1.17.1

# Run each metric module on its own (all read output/mimic_demo_clean.csv directly)
python fidelity_metrics.py
python utility_eval.py
python membership_inference.py
python attribute_inference.py
```

No flags, no config files. Each script's `main()` is the reference invocation. The runner that emits contract JSON is in B2.

---

## Key Decisions

**Why build and test evaluation code before any generator exists?** The protocol and code don't have a Track 1 dependency, only the data does — using the real train split as a stand-in synthetic dataset means the code gets written and debugged now, with zero rewrite needed when real synthetic data arrives (just swap the input file). See ADR-005.

**Why AUROC instead of accuracy for the utility metric?** `hospital_expire_flag` is a 31%/69% split, not balanced — accuracy on an imbalanced target rewards always-predicting-the-majority-class, which AUROC doesn't.

**Why does the membership-inference attack use nearest-neighbor distance instead of model confidence scores?** The target being attacked is a data generator, not a classifier — a generator has no "confidence output" to query. Nearest-neighbor distance between a candidate record and the synthetic dataset is the standard proxy: records the generator memorized should sit closer to at least one synthetic point than records it never saw.

**Why is the attribute-inference attack's 0.0 uplift not reported as a privacy success?** (Superseded by [`attribute_targets_result.md`](attribute_targets_result.md), which uses attributes both splits cover.) Because the cause was checked and it's a data artifact (the attacker never saw the target class in training — P-003), not evidence the generator/protocol resists attribute inference. Reporting it without that caveat would be the kind of unearned claim this documentation system exists to prevent.

---

## Outputs

| Output | Value |
|---|---|
| Evaluation protocol | [`eval_protocol.md`](../eval_protocol.md) |
| Fidelity metrics module | `fidelity_metrics.py` |
| Utility pipeline module | `utility_eval.py` |
| Membership-inference module | `membership_inference.py` |
| Attribute-inference module | `attribute_inference.py` |
| Downstream utility label | `hospital_expire_flag` |
| Result writeups | [`fidelity_result.md`](fidelity_result.md), [`utility_result.md`](utility_result.md), [`membership_inference_result.md`](membership_inference_result.md), [`attribute_inference_result.md`](attribute_inference_result.md) (all stand-in runs) |
| Phase 2 | [`B2_eval_runner.md`](B2_eval_runner.md) |
