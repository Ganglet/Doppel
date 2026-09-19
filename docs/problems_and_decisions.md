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

