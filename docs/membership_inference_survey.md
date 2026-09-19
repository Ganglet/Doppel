# Membership Inference Survey — what the literature says and where Doppel's attacks sit (2026-09-19)

Closes the Phase 1 task "survey membership-inference attack methodology (shadow-model approach)" from the blueprint. It is a reference for the [evaluation protocol](../eval_protocol.md) and the [Phase 2 doc](B2_eval_runner.md), not a measured result.

---

## How this was checked, and its limits

Every source below was looked up on 2026-09-19 against its arXiv record, publisher page, PoPETs page or PMC page, and the title, authors and year are as those pages show them. Two limits:

- **I read abstracts and summary pages for most papers, not the full text.** Statements about what a paper found are limited to what that page says. The two EHR benchmarks (Yan et al., Chen et al.) were read in more detail, because their privacy methods are the closest match to this project. Anything that goes beyond the source is marked *(my reading)*.
- **Venues I could not confirm are left out.** Where a record shows only arXiv, the entry gives only the arXiv ID.

---

## 1. The problem and the threat model

Membership inference asks, for a record `x` and access to a trained model or a released dataset, whether `x` was in the training set. What varies between papers is what the attacker can see and what they already know.

| Assumption | Where it appears | Doppel's setting |
|---|---|---|
| Attacker holds the exact candidate record | assumed throughout | Same: every attack scores real train and holdout rows |
| Attacker can train shadow models on data from the same distribution | Shokri et al. [1] | Same, and generous: shadow member sets are drawn from the train set itself |
| Attacker knows the model type | shadow-model attacks [1]; relaxed in [3] and [8] | Same: shadow generators are the same class as the target |
| Attacker needs auxiliary data | assumed in [1]; removed in [15] | Assumed, so results are closer to a worst case |
| Attacker sees only the released synthetic data | [15] | Not modelled separately |

*(my reading)* Doppel's shadow-model setup therefore makes the strongest of the common assumptions, which is the right direction for a privacy score but means the numbers are a worst-case reading, not a typical-attacker reading.

---

## 2. Attack families

| Family | Sources | How it works, per the sources | Needs |
|---|---|---|---|
| Shadow-model attack | Shokri et al. [1] | Trains an inference model to "recognize differences in the target model's predictions on the inputs that it trained on versus the inputs that it did not" | Black-box access, shadow models |
| Relaxed-assumption attack | Salem et al. (ML-Leaks) [3] | Relaxes the key assumptions of the shadow-model attack; reports it works across eight datasets at low cost | Fewer assumptions than [1] |
| Overfitting-based | Yeom et al. [2] | Analyses how overfitting and influence enable membership inference and attribute inference; reports overfitting is not strictly necessary for attacks to succeed | Model access *(my reading)* |
| Likelihood-ratio and calibration | Carlini et al. (LiRA) [4], Watson et al. [5] | [4] argues existing evaluation metrics are inadequate and reports LiRA is "10x more powerful" at low false-positive rates; [5] adjusts membership scores by how hard each sample is, to cut false positives | Trained reference models *(my reading)* |
| Attacks on generative models | Hayes et al. (LOGAN) [7], Hilprecht et al. [8], Chen et al. (GAN-Leaks) [9] | [7] uses a GAN's discriminator, white-box and black-box; [8] gives one attack that assumes no model type and one that targets VAEs; [9] gives a taxonomy, new attacks and a calibration technique | Generator access, varies |
| Synthetic tabular data | Stadler et al. [10], van Breugel et al. (DOMIAS) [12], Houssiau et al. (TAPAS) [13], Meeus et al. [14], Guépin et al. [15] | [10] evaluates inference attacks against several generators; [12] targets "local overfitting" with a density-based attack, strongest on underrepresented samples; [13] is a toolbox of attacks that generalise prior work; [14] identifies vulnerable records from the distance to a record's closest neighbours; [15] removes the auxiliary-data assumption | Released synthetic data, sometimes generator access |
| Distance to closest record | Platzer and Reutterer [11], Yan et al. [17], Chen et al. (SynthEHRella) [18] | Score a real record by how close it is to the synthetic set; [11] uses the share of synthetic records closer to a training record than to a holdout record, where about 50% indicates no memorization | Released synthetic data only |

Two points from the sources bear directly on this project:

- **Shadow modelling is standard for synthetic data, and expensive.** Meeus et al. state in their abstract that shadow-model MIAs "have become the standard approach to evaluate the privacy risk of synthetic data", and that they require many generated datasets and trained models to assess one record [14]. Doppel uses 8 shadow generators per run.
- **Distance-based scoring is not proof of privacy.** Ganev and De Cristofaro report a reconstruction attack (ReconSyn) that "can recover 78-100% of the outliers in the train data with only black-box access" from synthetic datasets that still pass existing similarity-based privacy tests [16].

---

## 3. Attribute inference

| Source | What it says |
|---|---|
| Yeom et al. [2] | Overfitting lets an attacker extract sensitive attributes as well as infer membership |
| Jayaraman and Evans [6] | Asks whether attribute inference is just imputation. Per the abstract, earlier and black-box attacks give limited insight beyond imputation, while their white-box attacks identify records with specific sensitive attributes that imputation cannot |
| Yan et al. [17], Chen et al. [18] | Both define attribute inference on synthetic EHR data as a 1-nearest-neighbour match to the known attributes, then read off the missing one |

*(my reading)* The distinction in [6] is the reason the Doppel attribute attack reports a **member gap** and not raw accuracy: uplift on records the generator never saw is imputation, and only the extra accuracy on training records is specific to membership. See [`attribute_targets_result.md`](attribute_targets_result.md).

---

## 4. Evaluation metrics

| Issue | Source | Consequence for reporting |
|---|---|---|
| Existing evaluation metrics are inadequate, and attack power is measured at low false-positive rates | Carlini et al. [4] | Report true-positive rate at a low false-positive rate as well *(my reading: average-case AUROC can hide a confident attack on a few records)* |
| Scores depend on how hard each record is | Watson et al. [5] adjust scores by per-sample difficulty; Chen et al. [9] also propose a calibration technique | Read an attack against a known ceiling and floor, not on its own |
| A distance score needs a reference for "no memorization" | Platzer and Reutterer [11] | Their reference is a holdout set, about 50% |
| A few vulnerable records can matter more than the average | Meeus et al. [14], Ganev and De Cristofaro [16] | Look at which records leak, not only the mean |

---

## 5. What EHR benchmarks report

| Benchmark | Privacy method | Main privacy finding |
|---|---|---|
| Yan et al., Nature Communications 2022 [17] | Attribute inference by 1-NN with Euclidean distance; membership inference that claims membership if some synthetic record is within a distance threshold (threshold 2); identity disclosure; nearest-neighbour adversarial accuracy | "All synthetic datasets achieved a lower privacy risk than the real data"; the sampling baseline posed the lowest risk overall and EMR-WGAN the highest, with risks low across methods |
| Chen et al., JAMIA 2025 (SynthEHRella, the package the blueprint cites) [18] | Membership inference risk as the minimum Euclidean distance from each real record to the synthetic set; attribute inference risk by 1-NN on the known attributes | "Rule-based methods excel in privacy protection"; Synthea and Plasmode gave the lowest membership and attribute risk on MIMIC-III and MIMIC-IV |

*(my reading)* The Doppel membership attacks belong to the same distance-based family as [17] and [18], with two additions they did not need: shadow models to turn a distance into a calibrated score, and a ceiling and floor to read it against.

---

## 6. Where Doppel's attacks sit

| Doppel component | Literature counterpart | Match |
|---|---|---|
| `evaluation/membership_inference.py` shadow wrapper with leave-one-shadow-out scoring | Shokri et al. [1]; standard for synthetic data per [14]; toolbox in [13] | Same idea, small scale (8 shadow generators) |
| `numeric4`, `gower`, `icd9_codes` distances | Min-distance membership risk in [18], distance threshold in [17], DCR in [11] | Same family. Gower and code-set Jaccard are my choices for mixed-type and set-valued columns *(my reading)* |
| `evaluation/mia_calibration.py` ceiling (exact copy) and floor (unseen real rows) | Calibration in [5] and [9]; the 50% reference in [11] | Same purpose, different construction |
| `evaluation/mia_direct_check.py` train vs holdout | Holdout comparison in [11] | Same design. The Doppel holdout differs in distribution from train (15 Puerto Rican admissions, none in train), which is why the same-distribution half-train diagnostic was added |
| `codes_once` vs `codes_repeated` diagnostic | Vulnerable-record identification in [14], underrepresented samples in [12], outliers in [16] | Consistent with all three: records with rare codes are the exposed ones. Not tested against a generator that suppresses rare codes |
| Attribute attack reporting a member gap | Imputation question in [6] | Direct implementation of the distinction |

---

## 7. Gaps between the protocol and the literature

Not yet implemented, in the order I would do them:

1. **True-positive rate at low false-positive rate.** Carlini et al. [4] argue existing evaluation metrics are inadequate and report attack power at low false-positive rates, and Doppel reports AUROC only. With 47 non-members per shadow world the smallest non-zero false-positive rate is about 2%, so any figure would be coarse. Worth adding with that caveat stated.
2. **Per-record vulnerability.** [14] and [16] point at individual records. The `codes_once` result suggests which records to look at, and no per-record report exists yet.
3. **A density-based attack.** DOMIAS [12] uses a reference density to correct for records in dense regions, which is close to the holdout confound Doppel hit. It needs a usable reference density, which 94 rows may not support.
4. **A release-only attacker.** [15] removes the auxiliary-data assumption. Doppel's shadow-world sets make the attacker stronger than that.
5. **Wording.** [16] shows a low similarity-based score does not establish privacy, so the report should say an AUROC near 0.5 means these attacks found nothing, not that the data is safe. This matches P-010.

---

## References

1. R. Shokri, M. Stronati, C. Song, V. Shmatikov. *Membership Inference Attacks against Machine Learning Models.* IEEE Symposium on Security and Privacy, 2017. [arXiv:1610.05820](https://arxiv.org/abs/1610.05820)
2. S. Yeom, I. Giacomelli, M. Fredrikson, S. Jha. *Privacy Risk in Machine Learning: Analyzing the Connection to Overfitting.* arXiv 2017, revised 2018. [arXiv:1709.01604](https://arxiv.org/abs/1709.01604)
3. A. Salem, Y. Zhang, M. Humbert, P. Berrang, M. Fritz, M. Backes. *ML-Leaks: Model and Data Independent Membership Inference Attacks and Defenses on Machine Learning Models.* NDSS 2019. [arXiv:1806.01246](https://arxiv.org/abs/1806.01246)
4. N. Carlini, S. Chien, M. Nasr, S. Song, A. Terzis, F. Tramer. *Membership Inference Attacks From First Principles.* arXiv 2021, revised 2022. [arXiv:2112.03570](https://arxiv.org/abs/2112.03570)
5. L. Watson, C. Guo, G. Cormode, A. Sablayrolles. *On the Importance of Difficulty Calibration in Membership Inference Attacks.* arXiv 2021, revised 2022. [arXiv:2111.08440](https://arxiv.org/abs/2111.08440)
6. B. Jayaraman, D. Evans. *Are Attribute Inference Attacks Just Imputation?* ACM CCS 2022. [arXiv:2209.01292](https://arxiv.org/abs/2209.01292)
7. J. Hayes, L. Melis, G. Danezis, E. De Cristofaro. *LOGAN: Membership Inference Attacks Against Generative Models.* Proceedings on Privacy Enhancing Technologies 2019(1). [arXiv:1705.07663](https://arxiv.org/abs/1705.07663)
8. B. Hilprecht, M. Härterich, D. Bernau. *Monte Carlo and Reconstruction Membership Inference Attacks against Generative Models.* Proceedings on Privacy Enhancing Technologies 2019(4), 232-249. [PDF](https://petsymposium.org/popets/2019/popets-2019-0067.pdf)
9. D. Chen, N. Yu, Y. Zhang, M. Fritz. *GAN-Leaks: A Taxonomy of Membership Inference Attacks against Generative Models.* ACM CCS 2020. [arXiv:1909.03935](https://arxiv.org/abs/1909.03935)
10. T. Stadler, B. Oprisanu, C. Troncoso. *Synthetic Data -- Anonymisation Groundhog Day.* arXiv 2020, last revised 2022. [arXiv:2011.07018](https://arxiv.org/abs/2011.07018)
11. M. Platzer, T. Reutterer. *Holdout-Based Empirical Assessment of Mixed-Type Synthetic Data.* Frontiers in Big Data 4, 2021. [DOI 10.3389/fdata.2021.679939](https://www.frontiersin.org/journals/big-data/articles/10.3389/fdata.2021.679939/full)
12. B. van Breugel, H. Sun, Z. Qian, M. van der Schaar. *Membership Inference Attacks against Synthetic Data through Overfitting Detection* (DOMIAS). arXiv 2023. [arXiv:2302.12580](https://arxiv.org/abs/2302.12580)
13. F. Houssiau, J. Jordon, S. N. Cohen, O. Daniel, A. Elliott, J. Geddes, C. Mole, C. Rangel-Smith, L. Szpruch. *TAPAS: a Toolbox for Adversarial Privacy Auditing of Synthetic Data.* NeurIPS 2022 SyntheticData4ML workshop. [arXiv:2211.06550](https://arxiv.org/abs/2211.06550)
14. M. Meeus, F. Guépin, A.-M. Creţu, Y.-A. de Montjoye. *Achilles' Heels: Vulnerable Record Identification in Synthetic Data Publishing.* ESORICS 2023. [arXiv:2306.10308](https://arxiv.org/abs/2306.10308)
15. F. Guépin, M. Meeus, A.-M. Cretu, Y.-A. de Montjoye. *Synthetic is all you need: removing the auxiliary data assumption for membership inference attacks against synthetic data.* ESORICS 2023 workshop DPM. [arXiv:2307.01701](https://arxiv.org/abs/2307.01701)
16. G. Ganev, E. De Cristofaro. *The Inadequacy of Similarity-based Privacy Metrics: Privacy Attacks against "Truly Anonymous" Synthetic Datasets.* IEEE Symposium on Security and Privacy, 2025. [arXiv:2312.05114](https://arxiv.org/abs/2312.05114)
17. C. Yan, Y. Yan, Z. Wan, Z. Zhang, L. Omberg, J. Guinney, S. D. Mooney, B. A. Malin. *A Multifaceted benchmarking of synthetic electronic health record generation models.* Nature Communications, 2022. [PMC9734113](https://pmc.ncbi.nlm.nih.gov/articles/PMC9734113/)
18. X. Chen, Z. Wu, X. Shi, H. Cho, B. Mukherjee. *Generating synthetic electronic health record data: a methodological scoping review with benchmarking on phenotype data and open-source software* (SynthEHRella). JAMIA 32(7), 2025. [PMC12203555](https://pmc.ncbi.nlm.nih.gov/articles/PMC12203555/), package: [github.com/chenxran/synthEHRella](https://github.com/chenxran/synthEHRella)
