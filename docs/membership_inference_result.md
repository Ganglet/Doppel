# Membership Inference Result — shadow-model attack harness correctly separates memorizing from noisy generators (2026-09-17)

Raw evidence for the claim that `membership_inference.py`'s shadow-model attack behaves correctly — i.e. it can actually detect membership leakage when leakage is present, and detect its absence when it isn't. Reproduce with `python membership_inference.py` from the repo root.

> **Stand-in run (Phase 1).** This measured real train against real holdout, not a generator. The same metric on real synthetic data is in [`baseline_evaluation_result.md`](baseline_evaluation_result.md) and [`B2_evaluation_phase2.md`](B2_evaluation_phase2.md).

> **Superseded for privacy claims:** the 4-column attack here reads 0.51 to 0.52 on real baselines while ICD-9 code sets read 0.64. See [`membership_calibration_result.md`](membership_calibration_result.md).

---

## Method (honest framing)

No real generator exists yet, so this can't measure a real generator's privacy. What it does measure: a self-validation test built into the harness. Two deliberately-constructed stand-in "generators" are attacked — one that memorizes (resamples real records with zero added noise) and one that adds Gaussian noise scaled to each column's standard deviation (`noise_scale=0.3`). Both are attacked with 8 shadow models and leave-one-shadow-out AUROC evaluation.

The point of this test is **not** "here is Doppel's privacy score" — it's "here is proof the attack code works before we trust it on a real generator." A harness that gave the same AUROC for both a memorizing and a noisy generator would be broken, or measuring nothing. This one doesn't. **Honest phrasing for the report: "the membership-inference attack implementation is validated against synthetic stand-in generators with known memorization properties; it has not yet been run against a real Track 1 generator."**

---

## Results

| Stand-in generator | `noise_scale` | Attack AUROC (mean, leave-one-shadow-out) | Interpretation |
|---|---|---|---|
| Memorizing | 0.0 | 0.8237 | Harness correctly detects strong membership leakage |
| Noisy | 0.3 | 0.6630 | Harness correctly shows leakage drops as noise increases |

Protocol threshold ([`eval_protocol.md`](../eval_protocol.md)): attack AUROC within 0.45–0.55 = good privacy, ≥ 0.65 = fail. Neither stand-in generator is a real candidate for Doppel's own privacy claim — they exist only to prove the attack code reacts correctly to known ground truth.

> **Note:** neither number should be quoted as "Doppel's membership-inference score." Both are calibration checks on synthetic stand-ins with artificially known behavior, not a measurement of any real generator.

---

## Raw evidence

```
$ python membership_inference.py
Sanity check - memorizing generator (noise_scale=0.0), expect attack AUROC near 1.0:
  mean attack AUROC: 0.8237

Noisy generator (noise_scale=0.3), expect attack AUROC closer to 0.5:
  mean attack AUROC: 0.6630
```

The memorizing case landed at 0.8237, not closer to 1.0 as the in-code comment predicted — worth noting honestly rather than editing the comment after the fact. Plausible reason: even exact resampling only reduces nearest-neighbor distance to zero for population records that were actually drawn into that shadow model's member set; on a small population, some noise remains in the attack signal regardless. This hasn't been investigated further; flagged here rather than smoothed over.
