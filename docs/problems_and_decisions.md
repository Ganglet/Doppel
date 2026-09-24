# Problems & Decisions Log

One running file for Project Doppel. Never split, never rewritten — only appended to.
ADRs and Problems are numbered independently and sequentially, oldest first.

---

## Architecture Decisions

### ADR-001 — Split train/holdout by `subject_id`, not `hadm_id`
**Decision:** The 80/20 train/holdout split is done at the patient level (`subject_id`), then all of a patient's admissions inherit that split.
**Why:** A single patient can have multiple admissions (`hadm_id`). Splitting at the admission level would let the same patient appear in both train and holdout, leaking patient-specific signal into the "held-out" evaluation.
**Impact:** Track 1's generators only ever train on `train`-split admissions. Track 2's utility/privacy evaluation always treats `holdout` as the untouched real-world test set. On a 100-patient dataset this produces slightly uneven admission counts per split (94/35, not exactly 80/20) — see P-003.
**Commit:** [`c7c177a`](https://github.com/Ganglet/Doppel/commit/c7c177a996d1e91e8f4ae84d65b85c44b43b9bf2)

---

### ADR-002 — Clip age at 89, flag with `age_89_plus` instead of using the raw MIMIC-III value
**Decision:** Ages computed from `DOB`/`ADMITTIME` are clipped at 89 and a separate boolean `age_89_plus` column is added, rather than passing the raw computed age through.
**Why:** MIMIC-III shifts date-of-birth for patients over 89 as a HIPAA de-identification step, which otherwise produces raw ages around 300. Treating that as a real value would corrupt any age-based feature or model.
**Impact:** Any downstream model (generator or evaluator) using `age` sees a capped, non-misleading value; anything that needs to know "this patient was actually 90+" should use `age_89_plus` instead.
**Commit:** [`c7c177a`](https://github.com/Ganglet/Doppel/commit/c7c177a996d1e91e8f4ae84d65b85c44b43b9bf2)

---

### ADR-003 — `hospital_expire_flag` chosen as the downstream utility label over `readmit_30d`
**Decision:** Track 2's train-on-synthetic/test-on-real utility evaluation targets `hospital_expire_flag` (in-hospital mortality), not `readmit_30d`.
**Why:** Checked class counts by split before deciding: `hospital_expire_flag` has 6 positive cases in the 35-row holdout set; `readmit_30d` has only 2. Any AUROC computed on 2 positives is statistical noise on this dataset size.
**Impact:** `readmit_30d` stays in the dataset as a secondary/stretch label if time allows, but all utility-pipeline results reported in [`utility_result.md`](utility_result.md) target `hospital_expire_flag`.
**Commit:** [`d197827`](https://github.com/Ganglet/Doppel/commit/d19782754c4f2daabe4807af92430e68c2453e39)

---

### ADR-004 — `icd9_codes` serialized as JSON, not a Python list repr
**Decision:** The `icd9_codes` column in `output/mimic_demo_clean.csv` is written with `json.dumps()` and must be read with `json.loads()`.
**Why:** The original implementation used `.apply(list)`, which pandas writes to CSV as a Python literal string (e.g. `['99591', '99662']`). That's not valid JSON — anyone reading the column with `json.loads()` (the obvious choice) would get a parse error, and the interface contract didn't say which parser to use.
**Impact:** Any code that consumes this column (Track 1's generators, Track 2's evaluation code) must use `json.loads()`. Documented explicitly in [`schema_and_feature_dictionary.md`](../schema_and_feature_dictionary.md) §8 so it isn't rediscovered the hard way.
**Commit:** [`6280b0e`](https://github.com/Ganglet/Doppel/commit/6280b0e2d6ef7abcb055b0bf22f9dca9b095179f)

---

### ADR-005 — Evaluation code built and self-tested against the real `train` split as a synthetic-data stand-in
**Decision:** Track 2's fidelity, utility, membership-inference, and attribute-inference code was written and validated before Track 1 produced any generator, by treating the real `train` split as a placeholder for synthetic data.
**Why:** Track 1 hadn't started, but the evaluation protocol and code didn't need to wait — building and testing the harness against real data (with the same shape and interface as future synthetic data) meant zero rewrite when real synthetic data arrives, just a swapped input.
**Impact:** Every number in [`fidelity_result.md`](fidelity_result.md), [`utility_result.md`](utility_result.md), [`membership_inference_result.md`](membership_inference_result.md), and [`attribute_inference_result.md`](attribute_inference_result.md) validates the *code*, not any generator's actual output. This must stay explicit in every writeup until real synthetic data exists.
**Commits:** [`8f7fefe`](https://github.com/Ganglet/Doppel/commit/8f7fefe59e873fa9c2983ebb538989a1efe705c8), [`1f87231`](https://github.com/Ganglet/Doppel/commit/1f87231c0641fa57e993311863790aba87ff588c), [`09f7958`](https://github.com/Ganglet/Doppel/commit/09f79584221ddf410ebf6521f2fc72ca45c67f06), [`2b259af`](https://github.com/Ganglet/Doppel/commit/2b259afb1579ceec1a21c0ed7bb6cbe39f681ac2)

---

### ADR-006 — One git branch per phase, named `track<N>-phase<M>-<short-task-desc>`
**Decision:** Each track's work on a given project phase lives on one branch, named with the track number, phase number, and a short kebab-case description of the phase's main task (e.g. `track2-phase1-eval-protocol`).
**Why:** Keeps phase-scoped work isolated and reviewable without branch proliferation per individual file or commit; the phase number in the name makes it obvious at a glance which blueprint phase a branch corresponds to.
**Impact:** When Phase 2 work starts on a track, a new `track<N>-phase2-<task>` branch is created rather than continuing to commit onto the Phase 1 branch.

---

### ADR-007 — Raw MIMIC-III source tables excluded from version control
**Decision:** `.gitignore` excludes all raw MIMIC-III Demo CSVs (`PATIENTS.csv`, `ADMISSIONS.csv`, `LABEVENTS.csv`, etc.), PhysioNet license/checksum files, and Python cache directories.
**Why:** These files are only needed locally to run `preprocess_mimic_demo.py`; committing them is unnecessary and, as a general practice for clinical source data, worth avoiding even when the specific dataset is de-identified and open-access.
**Impact:** Anyone re-running preprocessing locally won't accidentally commit raw source tables even with a broad `git add`.
**Commit:** [`6280b0e`](https://github.com/Ganglet/Doppel/commit/6280b0e2d6ef7abcb055b0bf22f9dca9b095179f)

---

### ADR-008 — One shared codec and a validated output contract for all generators
**Decision:** Every generator fits on the same 110-column modeling frame built by `generators/codec.py` and is decoded by the same code. Output goes through `generators/validate.py` before it's written, and a failing file is never written. Each run writes a manifest (seed, hyperparameters, training-CSV SHA-256, git commit). Synthetic CSVs are regenerated from the seed, not committed.
**Why:** The blueprint's claim is comparability. If each generator preprocessed the data its own way, a fidelity gap could come from encoding choices rather than the model. Committed synthetic files would go stale every time the codec changed, and they regenerate in about a second.
**Impact:** Track 2 can rely on the contract in [`A1_generative_modeling.md`](A1_generative_modeling.md) for any generator's output. Track 4's generation Job is `python -m generators.generate --generator <name> --seed <seed>`, and a non-zero exit means no file was produced. CTGAN/TVAE and the diffusion model plug in by subclassing `Generator`.
**Branch:** `track1-phase1-generator-interface`

---

### ADR-009 — ICD-9 codes: primary as categorical, frequent secondaries as multi-hot, the rest as a marginal tail
**Decision:** `icd9_primary` is a categorical column. Secondary codes in ≥ 5 train admissions (55 codes, 49% of secondary mentions) become multi-hot columns. The other 395 form a tail pool, where only the per-admission count is modeled and codes are drawn by train frequency on decode, independently of the row. `n_diagnoses` is derived from the decoded list.
**Why:** The blueprint names rare, high-dimensional codes as the hard case, so dropping `icd9_codes` would drop the problem. Codes seen in fewer than 5 of 94 admissions are individual records, not patterns. Modeling their combinations jointly is memorization, and those combinations are what re-identify a patient. Deriving `n_diagnoses` means the count can't contradict the list.
**Impact:** Synthetic `icd9_codes` preserve the frequent-code structure and the code-count distribution, but not rare-code co-occurrence. Code order after the primary isn't modeled. `min_count` is a CLI flag, and sweeping it is the Phase 3 rare-code ablation. Track 2's fidelity currently excludes `icd9_codes`, so a set-overlap metric is needed to score this.
**Branch:** `track1-phase1-generator-interface`

---

### ADR-010 — Statistical baseline is a Gaussian copula with Ledoit-Wolf shrinkage; independent marginals is the reference floor
**Decision:** The blueprint's statistical baseline is a Gaussian copula over empirical marginals, with the latent correlation shrunk toward the identity at the Ledoit-Wolf intensity. `independent_marginals` (shrinkage fixed at 1) ships as a reference floor, not as one of the three benchmarked families.
**Why:** 110 modeled columns vs 94 rows makes the empirical correlation matrix singular. Shrinkage keeps the copula well-defined, and Ledoit-Wolf picks the intensity from the data instead of a hand-set constant (fitted: 0.668). The floor makes every other number interpretable. A generator that can't beat exact marginals with zero dependence isn't learning structure.
**Impact:** The copula beats the floor on correlation preservation vs train (0.139 vs 0.160), but not by a margin that survives seed noise on utility. See [`baseline_generator_result.md`](baseline_generator_result.md).
**Branch:** `track1-phase1-generator-interface`

---

### ADR-011 — Synthetic patients are single-admission, with surrogate IDs outside MIMIC-III's ranges
**Decision:** Each synthetic row is its own patient. `subject_id` starts at 10,000,000, `hadm_id` at 20,000,000, and `split` is `"synthetic"`. `readmit_30d` is generated as a plain binary attribute.
**Why:** Emitting real IDs would be a direct privacy leak and would silently corrupt any join. Modeling multi-admission patients from 100 real patients isn't feasible, so the admission-level grain from Track 3 is kept.
**Impact:** The validator rejects any ID that collides with a real one. In synthetic data `readmit_30d` isn't backed by a second admission, which matters only if someone tries to re-derive it.
**Branch:** `track1-phase1-generator-interface`

---

### ADR-012 — Generators are reported as mean ± sd over seeds, never from a single seed
**Decision (Track 1, proposed to Track 2 for the evaluation protocol):** Every generator is run over multiple seeds (20 in the baseline result), and every metric is reported as mean ± sd.
**Why:** On this holdout, TSTR AUROC for one generator varies with SD ≈ 0.2 across seeds. Seed 42 of `independent_marginals`, which has zero feature-label dependence by construction, scored 0.713 / 0.784, above the TRTR ceiling, while its 20-seed mean sits at chance (0.47 / 0.54). The holdout's 6 positives all fall in 20 of its 35 rows, which is where the noise comes from.
**Impact:** A single-seed number can put a signal-free generator above the real-data ceiling, so single-seed numbers don't go in the report or on the Pareto frontier. The "TSTR within 0.10 of TRTR" threshold in [`eval_protocol.md`](../eval_protocol.md) is smaller than one seed's noise and needs to be read against the seed spread.
**Branch:** `track1-phase1-generator-interface`

---

### ADR-013 — Code under MIT, data under ODbL 1.0
**Decision:** Repository code is MIT-licensed ([`LICENSE`](../LICENSE)). Data files derived from MIMIC-III Demo, including the committed files in `output/` and any synthetic data generated from them, stay under the Open Data Commons Open Database License v1.0 ([`DATA_LICENSE.md`](../DATA_LICENSE.md)).
**Why:** The repo had no license. MIMIC-III Demo v1.4 is published under ODbL 1.0 (verified on its PhysioNet page), and a code license can't relicense a derivative database. Keeping MIT verbatim in `LICENSE` lets GitHub detect it.
**Impact:** Anyone reusing the code can do so under MIT. Anyone redistributing the data or synthetic output must attribute MIMIC-III Demo and keep ODbL terms.
**Branch:** `track1-phase1-generator-interface`

---

### ADR-014 — Evaluation output is contract JSON from `eval_runner.py`, scored against real train
**Decision:** `eval_runner.py` scores one synthetic CSV and writes `results/<generator>_seed<n>.json` in the shape of `contracts/schemas/evaluation_result.schema.json`, validating it before writing. Fidelity is measured against real **train**; utility and attribute inference test on the real holdout. `results/` is gitignored and regenerated from the seed, like synthetic CSVs (ADR-008).
**Why:** The schema forbids extra top-level keys, so everything lives under `metrics.fidelity`, `metrics.utility` and `metrics.privacy`. Train is what the generator was fit on, so it is the right reference for "does the model reproduce its training distribution"; real-vs-holdout is only the sampling-noise floor.
**Impact:** Track 4's aggregation reads these files. Numbers in [`baseline_evaluation_result.md`](baseline_evaluation_result.md) are not comparable to the earlier fidelity numbers in [`fidelity_result.md`](fidelity_result.md), which used the holdout as the reference.
**Branch:** `track2-phase2-eval-runner`

---

### ADR-015 — Fidelity correlation and utility thresholds replaced by noise-floor references
**Decision:** The absolute correlation thresholds (0.10 / 0.20) and the "TSTR within 0.10 of TRTR" utility threshold in [`eval_protocol.md`](../eval_protocol.md) are dropped. Correlation is reported against the real-vs-real floor (0.203) and the `independent_marginals` baseline (0.163). Utility is reported as mean ± sd over 20 seeds, compared by Welch test.
**Why:** Real train vs holdout already scores 0.203, so no generator could pass the correlation threshold against the holdout, and the seed sd of TSTR (0.15 to 0.22) is bigger than the 0.10 utility threshold. A threshold below the noise floor decides pass/fail by the seed. This follows Track 1's caveats 2 and 3 in [`baseline_generator_result.md`](baseline_generator_result.md), which I checked and agree with.
**Impact:** Nothing is gated on correlation or utility until a larger holdout exists. The JSD threshold (0.10 / 0.20) stays, because generators land at 0.018 against a floor of 0.099.
**Branch:** `track2-phase2-eval-runner`

---

### ADR-016 — The privacy score is the strongest realistic membership attack, read against a ceiling and floor
**Decision:** Membership inference is run as three attacks (`numeric4`, `gower`, `icd9_codes`), and the highest mean AUROC is the generator's privacy score. Each run is read against two calibration arms from `mia_calibration.py`: an exact-copy generator (ceiling, 1.000) and real rows the generator never saw (floor, 0.49 to 0.50). The `codes_once` and `codes_repeated` attacks use train code frequencies an attacker wouldn't have, so they are diagnostics and are never scored. A band between 0.55 and 0.65 is now "review", since the original bands left it undefined.
**Why:** The 4-column attack scored both baselines at 0.51 to 0.52, inside the "good" band, while a code-set attack scores them at 0.64. A privacy metric that reads "safe" because the attack cannot see the leak is worse than no metric.
**Impact:** Track 4's Pareto frontier should use the max-over-attacks membership score, not `membership_inference` alone. Results JSON now carries `membership_inference` and `membership_inference_gower`; the code-set attack is in `mia_calibration.py` output, not yet in the contract JSON.
**Branch:** `track2-phase2-eval-runner`

---

### ADR-017 — Attribute inference reports the member gap on attributes both splits cover
**Decision:** Attribute inference targets `gender`, `first_careunit` and an age bucket, scores members (train) and non-members (holdout) separately with balanced accuracy minus chance, and treats the member gap as the privacy number. The ethnicity version stays in the code and results JSON but is not scored.
**Why:** The ethnicity target had a class missing from train (P-003), and scoring only holdout rows measured general inference, which is not a privacy leak. Balanced accuracy stops a shifted class mix from faking an uplift.
**Impact:** The results JSON carries `attribute_inference_targets` next to the old `attribute_inference`. No threshold is set, because real data barely supports inferring these attributes on unseen rows (uplift −0.120, 0.032, 0.096) and a threshold would be decided by seed noise. Track 4 should not chart the old ethnicity number.
**Branch:** `track2-phase2-eval-runner`

---

### ADR-018 — The Pareto frontier uses worst-case membership risk and is bootstrapped over seeds
**Decision:** `pareto.py` uses three axes: mean JS divergence vs train (lower), mean of the two TSTR AUROCs (higher), and `membership_worst_case` (lower, the max over the three realistic membership attacks). A generator is on the frontier if no other is at least as good on all three and strictly better on one. Frontier membership and pairwise dominance are bootstrapped over seeds, and the code-set attack is now in the results JSON.
**Why:** A single-seed or single-attack frontier can put a signal-free generator on top (ADR-012, ADR-016). Using the worst case stops a weak attack from reading as privacy.
**Impact:** Track 4 charts these keys, not `membership_inference` alone. Fidelity leaves out correlation, the one fidelity metric that separates the baselines, so a fourth axis may be needed. The whole evaluation, calibration and frontier must be rerun when CTGAN/TVAE and the diffusion model exist.
**Branch:** `track2-phase2-eval-runner`

---

### ADR-019 — Track 2 code lives in an `evaluation/` package
**Decision:** The nine Track 2 scripts moved from the repo root into `evaluation/`, mirroring `generators/`. They run from the repo root as `python -m evaluation.<module>` and import each other as `from evaluation.<module> import ...`.
**Why:** The root held nine flat scripts next to every other track's files, while Track 1 already used a package. A package also lets the scripts import each other without path tricks.
**Impact:** `python eval_runner.py` and the other old commands no longer work. Forward-looking docs (README, protocol, B1, B2, the result docs) now use the new commands. Earlier entries in this log and other tracks' docs keep the old flat paths as written, since this log is append-only. Git records the moves as renames, so file history follows. Before and after the move, regenerated `results/*.json` and `results/calibration/mia_calibration.json` were byte-identical and every script printed the same numbers. `preprocess_mimic_demo.py`, `eval_protocol.md` and `schema_and_feature_dictionary.md` stay at the root because other tracks' docs link to them.
**Branch:** `track2-phase2-eval-runner`

---

### ADR-020 — CTGAN and TVAE run from the `ctgan` library directly, on CPU with one torch thread
**Decision:** The GAN-family arm wraps `ctgan.CTGAN` and `ctgan.TVAE` (v0.12.1) as `Generator` subclasses in `generators/ctgan_tvae.py`, not SDV's `CTGANSynthesizer`/`TVAESynthesizer`. Training runs on CPU with `torch.set_num_threads(1)`.
**Why:** SDV's wrappers re-detect column types and apply their own RDT transforms, which would stack a second preprocessing layer on top of the shared codec and break ADR-008. CTGAN's internal mode-specific normalization is part of the method, so that stays. One thread was profiled at 1.5–2.2× faster than eight on these small matrices (CTGAN 100 epochs: 11.7 s vs 17.7 s). A fixed thread count also keeps floating-point reduction order, and so the output, the same on any machine.
**Impact:** Same seed gives byte-identical CSVs for both models. On 94 rows one epoch is one gradient step (`steps_per_epoch = max(n // batch_size, 1)`), so `epochs` is effectively the step count. `ctgan` and `rdt` are BUSL-1.1 (source-available, non-production use permitted), which is fine for this project but matters if an image bundling them is ever published.
**Branch:** `track1-phase2-generator-training`

---

### ADR-021 — Model selection happens inside train only: patient folds, DCR memorization, fidelity to the fit rows
**Decision:** Hyperparameters are compared with `generators/sweep.py`. Train is split into 5 patient-level folds (fixed fold seed, so every generator sees the same folds). For each fold, the generator fits on 4/5 of train. It's scored on fidelity to those fit rows (Track 2's `run_fidelity_report`) and on memorization against the unseen fifth (`generators/diagnostics.py`): the DCR ratio (median distance from synthetic rows to the fit rows, divided by the same for real unseen rows, using Gower distance) and the near-copy rate. Every config is run over several seeds.
**Why:** The holdout is Track 2's evaluation set (ADR-001), so choosing hyperparameters by holdout score would leak it into the benchmark. Fidelity to the fit rows alone rewards copying, since a generator that copies scores perfectly. DCR against unseen real rows is what separates learning from copying. The diagnostic was calibrated before use: real unseen rows score exactly 1.0 (near-copy 0.059), and exact copies score 0.0 (near-copy 1.0).
**Impact:** A config only counts if it improves fidelity while keeping `dcr_ratio ≥ 0.95` and `near_copy_rate ≤ 0.10` (twice what real unseen rows score). Sweep outputs go to `output/sweeps/` (regenerated, not committed). The numbers are in [`sweep_result.md`](sweep_result.md).
**Branch:** `track1-phase2-generator-training`

---

### ADR-022 — Generator output contract reconciled with Track 4's `generator_output.schema.json`
**Decision:** Manifests written by `generate` carry every field Track 4's schema requires (`run_id`, `generator_name`, `generator_version`, `input_dataset_id`, `output_path`, `output_format`, `num_records`). The schema is amended so the `generator_name` enum matches the real generators, `seed` is required, and the reproducibility fields are declared (`hyperparams`, `train_rows`, `train_csv_sha256`, `codec`, `git_commit`, `created_utc`). `additionalProperties: false` stays.
**Why:** Validated against the Phase 1 draft schema, every manifest failed. `gaussian_copula` wasn't a permitted name, and the strict schema rejected the seed and training-data hash, which is the information ADR-012 and the blueprint's reproducibility goal depend on. The draft asked all tracks to review before implementation, and cross-track contracts are Track 1's call.
**Impact:** All four generators' manifests now validate, and a manifest without a seed or with an undeclared field still fails. `input_dataset_id` is content-addressed (`mimic_demo_clean@<sha256[:12]>`), so a change to the cleaned data is visible in every downstream result. The `data/` vs `output/` path mismatch in `contracts/README.md` is left for Tracks 3 and 4. Track 1's CLI takes explicit paths either way.
**Branch:** `track1-phase2-generator-training`

---

### ADR-023 — Track 1 runs on the team's root pins, plus a neural-extras file
**Decision:** The copula and `independent_marginals` need nothing beyond the root `requirements.txt` (Track 2's pins, installed by Track 4's `python:3.11-slim` image). `generators/requirements-neural.txt` includes it with `-r ../requirements.txt` and adds torch 2.14.0, ctgan 0.12.1 and rdt 1.22.0 for CTGAN, TVAE and the diffusion model. My earlier separate core file, which pinned numpy 2.5.3, is removed.
**Why:** numpy 2.5.3 requires Python ≥ 3.12, so my pins would have forced a different image from the rest of the team, and one pipeline should run on one environment. The full neural stack installs and runs on Python 3.11.5 with numpy 2.4.6. After the Cholesky fix (P-013), all four generators give byte-identical output on that environment and on Python 3.12 / numpy 2.5.3, so aligning costs nothing in reproducibility.
**Impact:** The generator image is Track 4's base image plus `generators/requirements-neural.txt`, with torch from the CPU index on Linux. There's no Python version change. Every Track 1 number from 2026-09-20 on is produced on this environment.
**Branch:** `track1-phase2-generator-training`

---

### ADR-024 — Initial sweep outcome: the copula leads at this n, CTGAN underfits, TVAE memorizes
**Decision:** Configs carried into Phase 3: `gaussian_copula` with shrinkage 0.25, and `ctgan` at 300 epochs (least-bad). No `tvae` config passes the memorization guard. TVAE is proposed to Track 2 as the positive control for membership inference.
**Why:** From 165 fits (11 configs × 3 seeds × 5 patient folds, [`sweep_result.md`](sweep_result.md)):
- **Copula:** λ = 0.25 gives the best correlation difference of any config that passes the guard (0.119 vs 0.148 for Ledoit-Wolf). Its near-copy rate is 0.021, below the 0.059 that real unseen rows score.
- **CTGAN:** no epoch count beats the independent-marginals floor on either fidelity metric (JSD 0.103–0.139 vs 0.020, correlation 0.177–0.180 vs 0.175), and longer training makes it worse. The failure sits in the continuous columns, where the hospital-stay median comes out at 11.9 days vs 6.7 real.
- **TVAE:** 52–71% of rows are near-copies, rising with training. It collapses onto 20 of 65 primary codes, and 34% of its rows reproduce a real patient's key fields.

**Impact:** At 94 training rows, the classical baseline beats both neural generators, and that's the expected small-data result, not a tuning gap. The next sweep tests the obvious counter-argument, that the defaults are too big for 75 rows: smaller CTGAN/TVAE networks, fewer TVAE epochs, and stronger TVAE regularization (`l2scale`), plus copula shrinkage below 0.25. For Track 2, TVAE is a real generator that verifiably memorizes, so an attack that rates TVAE as safe is too weak to trust on the others. The diffusion generator's acceptance bar in [`A2_generator_training.md`](A2_generator_training.md) is the λ = 0.25 copula.
**Branch:** `track1-phase2-generator-training`

---

### ADR-025 — Track 2 evaluates five named arms, with TVAE as the positive control
**Decision:** `evaluation/arms.py` defines each evaluated configuration as a generator plus hyperparameters: `independent_marginals`, `gaussian_copula` (Ledoit-Wolf), `gaussian_copula_shrink025`, `ctgan` (300 epochs) and `tvae` (300 epochs). `--generator` takes an arm name. The runner regenerates each arm's data on every run into `output/synthetic/eval/<arm>/`, and shadow generators are fitted with Track 1's `synthesize` and cached on disk under a key made from the `generators/` source, the dataset, the hyperparameters, the seed and the exact member rows.
**Why:** Track 1 carried the 0.25-shrinkage copula and 300-epoch CTGAN into Phase 3 and proposed TVAE as the membership positive control (ADR-024). A configuration has to be a named, reproducible object for runs to be comparable, and the always-regenerate rule and content-keyed cache stop results mixing generator code versions (P-015).
**Impact:** `run_id` and `generator_name` in the results JSON are arm names, so Track 4 groups by arm. Evaluating a retuned or new generator is one line in `arms.py`, and everything downstream has to be rerun when Track 1's next sweep changes a config. `ctgan` and `rdt` are BUSL-1.1, source-available and non-production, so the neural arms carry that licence note.
**Branch:** `track2-phase3-full-evaluation`

---

### ADR-026 — Membership reporting adds pooled TPR at low FPR and a per-record report; a neighbourhood-count attack was tried and dropped
**Decision:** Every membership attack reports the pooled true-positive rate at 5% and 1% false-positive rate next to its AUROC. `evaluation.mia_calibration` reports each record's attack advantage against its number of once-seen codes. A feature counting synthetic rows in each record's neighbourhood was not added to the attack. The privacy axis of the Pareto frontier stays the worst-case AUROC.
**Why:** The survey listed both as gaps (Carlini et al. on low false-positive rates, Meeus et al. on vulnerable records). TVAE's AUROC is a moderate 0.68 while its pooled TPR at 1% FPR is 0.058 against a floor of 0.009, so AUROC alone understates that it identifies a few records confidently. The count feature changed AUROC by −0.013 to 0.000 in 3 seeds, so it adds nothing. TPR is not the Pareto axis because the 1% figure rests on about 376 pooled non-members and carries a seed sd of about 0.02.
**Impact:** Membership blocks in the results JSON carry `tpr_at_fpr_5pct` and `tpr_at_fpr_1pct`. Two survey gaps stay open: a density-based attack and a release-only attacker. Revisit TPR as an axis if a larger dataset gives a stabler estimate.
**Branch:** `track2-phase3-full-evaluation`

---

### ADR-027 — The Pareto frontier is reported with a sensitivity table and read against the positive control
**Decision:** `evaluation.pareto` recomputes frontier membership under eight axis sets (a correlation axis, one classifier, one attack at a time, no utility axis) and prints the privacy ordering per attack. A frontier is not reported without that table. This extends ADR-018.
**Why:** With five arms and seed sds this large every arm is non-dominated, which read alone looks like five wins. The sensitivity table showed TVAE's place depends only on utility (frequency 0.00 without that axis) and that a 4-column privacy axis would make TVAE look safest (0.98).
**Impact:** Track 4's dashboard should show pairwise dominance probabilities and the sensitivity, not only the frontier set, and the report should not rank generators from the frontier. Rerun when the diffusion model or a retuned generator arrives.
**Branch:** `track2-phase3-full-evaluation`

---

## Problems Encountered

### P-001 — `SimpleImputer` not fitted during utility-pipeline cross-validation
**Week/Date:** 2026-09-17
**Problem:** `utility_eval.py`'s `trtr_baseline()` crashed on the first fold with:
```
sklearn.exceptions.NotFittedError: This SimpleImputer instance is not fitted yet. Call 'fit' with appropriate arguments before using this estimator.
```
**Fix:** `build_features()` was creating a fresh, unfitted `SimpleImputer` on every call instead of reusing the one fitted on the training fold. Changed the function signature to accept and thread through the fitted `num_imputer` on transform-only calls, the same way the `OneHotEncoder` was already being threaded through.
**Lesson:** When a fit/transform helper function fits multiple objects (encoder, imputer, scaler), audit that *every* fitted object is threaded through the transform-only call path — it's easy to get the first one right and miss the second.

---

### P-002 — Logistic regression failing to converge in the utility pipeline
**Week/Date:** 2026-09-17
**Problem:** `LogisticRegression` raised repeated `ConvergenceWarning: lbfgs failed to converge after 1000 iteration(s)` during 5-fold CV, even at `max_iter=1000`.
**Fix:** Added a `StandardScaler` on numeric features (lab values, LOS in days, age — all on very different scales) before fitting, instead of raising `max_iter` further.
**Lesson:** A logistic regression convergence warning on tabular data with mixed-magnitude numeric features is usually a scaling problem, not an iteration-count problem.

---

### P-003 — Attribute-inference attack always predicted the majority class
**Week/Date:** 2026-09-17
**Problem:** `attribute_inference.py`'s attacker (target: `ethnicity`) scored exactly at the base rate (0.5143 accuracy, 0.0000 uplift) — it was predicting `WHITE` for every holdout row.
**Fix:** No code fix — traced to the data: `HISPANIC/LATINO - PUERTO RICAN` is 15 of 35 holdout admissions (43%) but 0 of 94 train admissions, a direct consequence of ADR-001's patient-level random split on only 100 patients. Documented in [`eval_protocol.md`](../eval_protocol.md) and [`attribute_inference_result.md`](attribute_inference_result.md) rather than silently "fixed."
**Lesson:** On a 100-patient dataset, always check per-column class coverage between train and holdout before trusting a privacy-attack result — a "good" (low) attack score can mean the attacker genuinely couldn't infer the attribute, or it can mean the attacker never saw that class in training. Those are not the same finding.

---

### P-004 — Schema doc claimed a source table was used that the code never loaded
**Week/Date:** 2026-09-17
**Problem:** `schema_and_feature_dictionary.md` listed `D_ICD_DIAGNOSES.csv` as a used source table (for ICD-9 code descriptions), but `preprocess_mimic_demo.py`'s `load_raw()` never loaded it, and no ICD-9 description lookup file existed in `output/`.
**Fix:** Flagged in code review; fixed in commit `6280b0e` — `D_ICD_DIAGNOSES.csv` is now loaded and written out as `output/icd9_lookup.csv` (14,567 code→description rows).
**Lesson:** A schema/interface doc and the code it describes can silently drift apart even within the same original commit — worth an explicit check ("does the code actually load every table the doc lists?") as part of reviewing any data-prep deliverable.

---

### P-005 — `icd9_primary` loses its leading zero when read with default `pd.read_csv`
**Week/Date:** 2026-09-18
**Problem:** The CSV stores `icd9_primary` correctly as text (`0389`, septicemia), but `pd.read_csv` infers int64 and turns it into `389`, which is a different ICD-9 code. Then `icd9_primary` no longer equals the first element of `icd9_codes` (still strings), and joins against `output/icd9_lookup.csv` miss. It affects 12 of 94 train admissions.
**Fix:** `generators/schema.load_real()` reads the column with `dtype={"icd9_primary": str}`, and the validator rejects an integer `icd9_primary`. Track 2's scripts read the real and synthetic CSVs the same way, so their categorical comparisons stay consistent. Any code that joins `icd9_primary` to the lookup or compares it to `icd9_codes` needs the `str` dtype.
**Lesson:** Code columns that look numeric are identifiers, not numbers. Pin their dtype on read, the same way ADR-004 pinned the parser for `icd9_codes`.

---

### P-006 — Track 3's branch didn't follow ADR-006 naming
**Week/Date:** 2026-09-18
**Problem:** Track 3's Phase 1 branch was named `track3-data-prep`, missing the phase number required by ADR-006. It was also briefly set as the repository's default branch instead of `main`.
**Fix:** The default branch was reset to `main`, and the branch was renamed on GitHub to `track3-phase1-data-prep`. It had no open PRs and was already fully merged into `main`. To update a local clone: `git branch -m track3-data-prep track3-phase1-data-prep && git fetch origin && git branch -u origin/track3-phase1-data-prep track3-phase1-data-prep`.
**Lesson:** Check branch name and default-branch settings when opening the first PR from a track, before other tracks start branching.

---

### P-007 — Binary columns always scored JSD 0 in `fidelity_metrics.py`
**Week/Date:** 2026-09-19 (found by Track 1 on 2026-09-18, in `baseline_generator_result.md`)
**Problem:** `hospital_expire_flag` and `readmit_30d` went through 10-quantile binning. With only the values {0, 1} the bin edges collapse to one bin, so JSD was 0.0000 whatever the positive rate. Train mortality 36.2% vs holdout 17.1% scored 0.0000. `age_89_plus` was in neither column list, so it wasn't scored at all. My note in [`fidelity_result.md`](fidelity_result.md) that the 0.0000 came from similar positive rates was wrong.
**Fix:** Added `BINARY_COLS` (`hospital_expire_flag`, `readmit_30d`, `age_89_plus`) and routed them through the categorical path. They now score 0.0340, 0.0038 and 0.0112 on train vs holdout, and the first two match Track 1's independent calculation. The fidelity report covers 52 columns instead of 49.
**Lesson:** A metric that returns exactly 0.0000 on a column with a known distribution shift is a bug until proven otherwise. I explained the zero away instead of checking it.

---

### P-008 — Copula seed-42 utility differs between two machines (open)
**Week/Date:** 2026-09-19
**Problem:** For `gaussian_copula` seed 42, Track 1 reports TSTR 0.356 (LR) and 0.724 (RF). I get 0.931 and 0.672, reproducibly on my machine, through both `eval_runner.py` and a direct `utility_eval.tstr_eval` call. `utility_eval.py` is unchanged on `main`. Mean JSD agrees (0.0189 vs 0.016).
**Fix:** None yet. The cause is not confirmed. Different library versions changing the sampled rows is a candidate, but that is a guess. My versions: Python 3.11.9, numpy 2.4.6, scikit-learn 1.8.0, scipy 1.17.1.
**Lesson:** "Identical SHA-256 on rerun" only shows determinism on one machine. Pin dependency versions in the Track 4 image and re-check that a seed reproduces inside it. This also supports ADR-012: a single-seed number can't be compared across machines.

---

### P-009 — P-008 traced to `method="eigh"` in the copula's sampler (fix proposed to Track 1)
**Week/Date:** 2026-09-19
**Problem:** Follow-up to P-008. Fitting and sampling `gaussian_copula` seed 42 under numpy 2.4.6 and numpy 2.2.6 (same pandas 2.3.3, scikit-learn 1.8.0, scipy 1.17.1) gives different files: 71.2% of numeric cells (3,281 of 4,606) and all 94 rows differ, and TSTR moves from 0.931 / 0.672 to 0.770 / 0.483. `independent_marginals` is byte-identical across the two versions. The fitted 110×110 correlation matrix differs by at most 1.1e-16 and the latent Z matrix is exactly equal, so the fit is not the cause. Replacing `method="eigh"` with `method="cholesky"` in `rng.multivariate_normal` (`generators/copula.py:81`) on a scratch copy gives 0 differing cells at a 1e-6 tolerance across the same two numpy versions.
**Fix:** Not applied. `generators/` is Track 1's code, so the one-line change is proposed to Angshuman, with the caveat that it changes every copula sample (same distribution, different draws), so his 20-seed numbers would need regenerating. I have not verified which numpy version Angshuman runs. His setup pins pandas, scikit-learn and scipy but not numpy (`docs/A1_generative_modeling.md`, `docker/base/Dockerfile`), so a different build is the likely explanation for 0.356 vs 0.931, not a confirmed one. A `requirements.txt` with my tested versions is added at the repo root for Track 4 to use in the image.
**Lesson:** Eigendecomposition-based sampling is not reproducible across numpy/LAPACK builds even with a fixed seed and a matrix equal to 1e-16, because eigenvectors are only defined up to sign and rotation within near-degenerate eigenspaces. Prefer a Cholesky factor when the matrix is positive definite, and check reproducibility across two library versions, not only across two runs on one machine.

---

### P-010 — The first membership attack understated leakage; found by calibrating it
**Week/Date:** 2026-09-19
**Problem:** The 4-numeric-column attack read 0.522 (copula) and 0.507 (independent marginals) over 20 seeds, and I wrote in [`baseline_evaluation_result.md`](baseline_evaluation_result.md) that both sat inside the privacy band. Adding a ceiling (exact copy, 1.000) and floor (never-seen real rows, 0.502) showed the attack had almost no room to detect anything on those columns, and an attack on ICD-9 code sets reads 0.639 and 0.638. Splitting the codes by train frequency gives 0.84 on the 286 codes seen once and 0.62 on the 197 seen 2+ times. A direct check on the real synthetic files was confounded: against all 35 holdout rows the Gower score read 0.62 to 0.65 but fell to 0.47 to 0.49 without the 15 Puerto Rican rows, because those rows are absent from train (P-003).
**Fix:** Added the Gower and code-set attacks, the calibration script, and the direct-check script; corrected the baseline writeup and rewrote the protocol's privacy section (ADR-016). The mechanism (a generator can only emit codes it saw, so a non-member's unique code never appears) fits the data but is untested against a generator that suppresses rare codes.
**Lesson:** An attack needs a known ceiling and floor before its output means anything. A score near 0.5 says "the attack found nothing", which is a claim about the attack until it has been shown to find something on a generator that leaks.

---

### P-011 — The member gap is biased by how the member and non-member sets differ
**Week/Date:** 2026-09-19
**Problem:** On `gender`, `independent_marginals` shows a member gap of 0.062 (one-sample p = 0.007) even though it destroys every cross-column relationship and cannot support attribute inference. The copula shows 0.056. The cause is the sets, not the generator: train is 47 F / 47 M and the 35-row holdout is 12 F / 23 M, so balanced accuracy on non-members drops for reasons unrelated to membership. The same set mismatch confounded the direct membership check (P-010).
**Fix:** None possible without a holdout that matches train. Each generator's gap is read against `independent_marginals` rather than against zero, and the writeup says so.
**Lesson:** Any "members vs non-members" comparison needs a null arm run through the same two sets. A gap that a no-dependence generator reproduces is a property of the split.

---

### P-012 — Members and non-members were scored on different Gower scales
**Week/Date:** 2026-09-19
**Problem:** My rewrite of `mia_direct_check.py` gave Gower AUROCs of 0.816 to 0.833 against 0.62 to 0.65 in the version it replaced, while the code-set numbers matched exactly. That split pointed at the one attack that has a scale. `gower_distances` divides each numeric column by the range of the rows it is given, and the rewrite scored train and holdout in separate calls, so holdout rows were measured on a different scale and looked systematically farther away.
**Fix:** Score members and non-members in one call (`pooled_scores` in `mia_direct_check.py`), which reproduces the earlier 0.622 and 0.648, and add a comment on `gower_distances`. The shadow-model attack was never affected because it scores one fixed population against each shadow generator.
**Lesson:** When a rewrite agrees with the old version for one attack and not the other, find what differs before trusting either number. A distance that normalises by its input is only comparable inside one call.


---

### P-013 — Fix for P-008 / P-009 applied: the copula samples through Cholesky, and output is identical across environments
**Week/Date:** 2026-09-20
**Problem:** Rayyan's diagnosis in P-009 is right, and the cause is structural rather than a numpy quirk. With 110 modeled columns and 94 rows the sample correlation matrix has rank at most 93, so after Ledoit-Wolf shrinkage exactly d − (n − 1) = 17 of its eigenvalues are identical (all equal to the shrinkage, 0.6676). Inside a repeated eigenvalue's subspace, `eigh` may return any orthonormal basis, and which one it returns depends on the LAPACK build. Reproduced on one machine: perturbing the fitted matrix by 1e-16 (the size of the cross-version difference P-009 measured) changes 99.1% of `eigh` draws, by up to 2.58, and 0.0% of Cholesky draws (max 2.9e-15). My runs used numpy 2.5.3 on Python 3.12, a third build next to Rayyan's 2.4.6 and 2.2.6. That's why the same seed gave 0.356, 0.770 and 0.931.
**Fix:** `generators/copula.py` samples with `method="cholesky"`, which is unique for a positive-definite matrix. That holds for any shrinkage above 0. All four generators (`gaussian_copula`, `independent_marginals`, `ctgan`, `tvae`) at seed 42 are now byte-identical between Python 3.11.5 / numpy 2.4.6 (the team `requirements.txt` and Docker image) and Python 3.12 / numpy 2.5.3. `independent_marginals` is unchanged by the fix (identity matrix), and every `gaussian_copula` number was regenerated: [`baseline_generator_result.md`](baseline_generator_result.md), [`sweep_result.md`](sweep_result.md), README Results 5–6. The copula's seed-42 TSTR is now 0.695 / 0.819 on every machine, and its 20-seed mean moved from 0.559 / 0.555 to 0.547 / 0.589, with the same conclusion. Track 1 now runs on the team's root pins, and `generators/requirements-neural.txt` adds torch and ctgan on top of them (ADR-023).
**Lesson:** `eigh` is only reproducible when the eigenvalues are distinct, and a d > n covariance guarantees they aren't. Check reproducibility across two library builds, not just two runs on one machine, which is what Track 2 did and what caught this.

---

### P-014 — The runner read synthetic CSVs with a plain `pd.read_csv`, so `icd9_primary` lost its leading zero
**Week/Date:** 2026-09-24 (introduced 2026-09-19)
**Problem:** Track 1's P-005 says `icd9_primary` must be read as text and that Track 2's scripts already read real and synthetic CSVs that way. My runner didn't: `load_synthetic` used a plain `pd.read_csv`, so `icd9_primary` came back as int64 and codes like `0389` became `389`. On the copula seed-42 file, 17 of 94 rows no longer matched the real column's strings. On that file the `icd9_primary` JSD was 0.284 instead of 0.142 and the mean JSD 0.0186 instead of 0.0158. The same column is a categorical predictor in the attribute attack, so those inputs were mismatched too. Every Phase 2 fidelity and attribute number was affected. Utility was not (the column is dropped) and neither were the membership attacks (shadow generators return decoded frames, not re-read CSVs).
**Fix:** `load_synthetic` reads through `generators.schema.load_real`, which pins the dtype. Fidelity numbers in [`full_evaluation_result.md`](full_evaluation_result.md) are not comparable to the Phase 2 ones for this reason and because the copula's rows are new draws since P-013.
**Lesson:** When another track logs an interface trap and says my code already handles it, check my code. I took that sentence on trust.

---

### P-015 — The runner reused a synthetic CSV made by older generator code
**Week/Date:** 2026-09-24
**Problem:** `eval_runner` used any existing `output/synthetic/<generator>_seed<n>.csv`. After Track 1's Cholesky fix (P-013) I reran copula seed 42 and the membership score moved from 0.6562 to 0.6486 while fidelity and TSTR did not move at all. The membership attack refits the generator each time, so it used the new code, and the other metrics read the old file. Results were a mix of old and new draws.
**Fix:** The runner always regenerates into `output/synthetic/eval/<arm>/`. Shadow-generator fits are cached on disk under `output/synthetic/shadow_cache/`, keyed by a hash of `generators/*.py`, the dataset CSV, the hyperparameters, the seed and the exact member rows, so changing any of them refits. Cold and warm cache runs give byte-identical results JSON.
**Lesson:** A cache needs a key that changes when what it caches changes. Reuse by filename alone is the same failure P-008 was about, one layer up.

---

### P-016 — I killed a working sweep because slow CTGAN looked like a hang
**Week/Date:** 2026-09-24
**Problem:** I launched the 100-run sweep with 12 workers. After about 25 minutes there were no results and each worker showed roughly 460 CPU-seconds, so I called it stuck and killed it. It was working. A 94-row CTGAN fit takes 48 s alone but 6.8 minutes with six running together (8.5× slower), so aggregate throughput at six workers is about 70% of running the fits one after another on this machine. The kill cost about 25 minutes.
**Fix:** Relaunched at 6 workers, added the shadow-fit cache (P-015) so calibration and the direct check reuse the runner's fits instead of refitting CTGAN.
**Lesson:** Before deciding a job is hung, compare per-process CPU growth against a solo timing and a measured concurrency scaling, since a slow run and a hung run look the same from outside. For CTGAN on this machine, more workers did not help.

