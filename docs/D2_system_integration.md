# Generator Containers, Kubernetes Jobs and Dashboard Scaffold

**Phase:** Phase 2 — Core Development (Weeks 3–7), commits `ae7b2c2`, `cf4f0fb`, `2be03c6` (2026-09-20) and `4a6c76d` (2026-09-21), branch `track4-phase2-system-integration-and-delivery-layer`, merged as PRs #7 and #8
**Owner:** Anshuman CE (Track 4 / Track D). Written up by Rayyan (Track 2) from the repository and the checks below; not yet reviewed by the owner
**Status:** Delivered as files. The dashboard was run headless and works; the Dockerfiles and Kubernetes Jobs were checked statically only, because the Docker daemon was not running where this was written. Six gaps found by reading them against the code they run are listed below and logged as P-017. There is no evaluation container or Job, and no pipeline wiring; Track 4's Phase 3 branch has no commits yet.

---

## Objective

Containerize each generator as it becomes available, give the generation stage Kubernetes Job templates, and scaffold a results dashboard, as the blueprint asks of this track in Phase 2. The point is that a generator can be run by anyone as a container instead of by reproducing someone's Python environment.

---

## What was built

### 1. Generator images

| Image | File | What it does |
|---|---|---|
| `doppel/statistical:0.1` | `docker/statistical/Dockerfile` | `python:3.11-slim`, copies the whole repository into `/app`, installs the root `requirements.txt`, and by default runs `python -m generators.generate --generator gaussian_copula --seed 42` |
| `doppel/ctgan:0.1` | `docker/ctgan/Dockerfile` | Same, but installs `generators/requirements-neural.txt` (torch, ctgan, rdt) from the CPU PyTorch index, and by default runs the `ctgan` generator with seed 42 |

The CPU index avoids the multi-GB CUDA wheel, as Track 1's `requirements-neural.txt` notes. The preprocessing image in the same directory family is Track 3's (see [`C2_data_validation.md`](C2_data_validation.md)).

### 2. Generation Jobs

| Job | Image | Command |
|---|---|---|
| `doppel-statistical` | `doppel/statistical:0.1` | `python -m generators.generate --generator gaussian_copula --seed 42` |
| `doppel-ctgan` | `doppel/ctgan:0.1` | `python -m generators.generate --generator ctgan --seed 42 --param epochs=1` |

Both are in the `doppel` namespace with `backoffLimit: 1`, `restartPolicy: Never` and `imagePullPolicy: IfNotPresent`. The CTGAN Job trains for one epoch, not the 300 epochs Track 1 carried into Phase 3.

### 3. Dashboard scaffold

`dashboard/app.py` (76 lines, Streamlit) lists the CSV files directly under `output/synthetic/`, and for the selected one shows the row and column counts, the total missing values, a 20-row preview, a table of column types and null counts, and the generator manifest next to it when present. It reads nothing else, so it shows none of the evaluation results, the Pareto frontier or the privacy scores.

### Checks I ran

| Check | Result |
|---|---|
| Dashboard run headless with Streamlit's test harness (streamlit 1.64.0, pandas 2.3.3) | No exceptions; title `Project Doppel`, the preview, column-information and manifest sections rendered, 40 datasets listed (20 `gaussian_copula` and 20 `independent_marginals` files from earlier local runs), first one shows 94 rows, 56 columns and 10 missing values |
| Dashboard with the unpinned `dashboard/requirements.txt` in a fresh environment | It resolved pandas 3.0.6, which this machine's Application Control policy blocked from loading; the same app ran fine with the team's pandas 2.3.3 |
| Kubernetes YAML parses | Both generation Jobs and the other three files parse |
| `docker build` of either image, or a Job run | Not run, the Docker daemon was not running |

### Gaps found by reading the files against the code they run (P-017)

1. **No `.dockerignore`, and both generator Dockerfiles run `COPY . /app`.** The whole build context goes into the image, including gitignored files such as raw MIMIC-III CSVs if they are present in the repository folder, the results folder and virtual environments.
2. **The generation Jobs mount no volume.** The generated CSV and manifest are written inside the container and disappear with the pod, so the dashboard and Track 2's evaluation cannot read what a Job produced.
3. **The preprocessing Job's volumes are not defined.** It names `mimic-raw-data-pvc` and `doppel-processed-data-pvc`, and no PersistentVolumeClaim exists anywhere in `k8s/`.
4. **The preprocessing Job sets no `RAW_DIR`,** so the script looks for the raw CSVs in `/app` and not in the mounted `/app/raw` (reproduced locally, the Job itself not run).
5. **`dashboard/requirements.txt` is unpinned,** while the rest of the project pins to `requirements.txt`.
6. **The CTGAN Job is a one-epoch run,** so its output is not evaluation-grade.

### Not done

- **No evaluation image or Job.** Stage 3 of the blueprint's pipeline is not containerized, so Track 2's code can only be run by hand.
- **No TVAE Job.** The CTGAN image installs the library TVAE needs, but there is no Job for it.
- **The dashboard shows no results.** It does not read `results/*.json`, so nothing in it shows the fidelity, utility or privacy numbers or the Pareto frontier.
- **No multi-stage pipeline** (preprocess, generate, evaluate, aggregate) and no end-to-end test; this is the Phase 3 branch `track4-phase3-pipeline-orchestration`, currently with no commits.
- **No record of any of this running on a cluster.** The earlier README's roadmap claimed local and minikube testing, which cannot be checked from the repository.

---

## Commands

```bash
# Dashboard (run headless and verified 2026-09-24 with these versions)
pip install streamlit pandas==2.3.3
streamlit run dashboard/app.py          # reads output/synthetic/*.csv from the repo root

# Generator images and Jobs (follow the files; NOT run here)
docker build -f docker/base/Dockerfile -t doppel/base:0.1 .
docker build -f docker/statistical/Dockerfile -t doppel/statistical:0.1 .
docker build -f docker/ctgan/Dockerfile -t doppel/ctgan:0.1 .
kubectl apply -f k8s/namespace/namespace.yaml
kubectl apply -f k8s/jobs/statistical-job.yaml
kubectl apply -f k8s/jobs/ctgan-job.yaml
kubectl logs -n doppel job/doppel-statistical

# The same generation step without containers (verified)
python -m generators.generate --generator gaussian_copula --seed 42
python -m generators.validate output/synthetic/gaussian_copula_seed42.csv
```

Expected from the last two commands: `PASS  wrote output/synthetic/gaussian_copula_seed42.csv ...` and `PASS  output/synthetic/gaussian_copula_seed42.csv  (94 rows)`.

---

## Key Decisions

**Why does the CTGAN image install from the CPU PyTorch index?** Track 1's `generators/requirements-neural.txt` says to install torch from the CPU index "to avoid the multi-GB CUDA wheel", and the image's `--extra-index-url` follows it.

**Why do the images build on the pinned `requirements.txt`?** Track 1 runs on the team's root pins so the whole pipeline uses one environment (ADR-023), and the image installs those same pins.

**Why does the CTGAN Job pass `epochs=1`?** Not stated in the repository. My reading is that it is a smoke configuration to prove the image runs quickly, since the 300-epoch default takes about 48 s per fit on a laptop and much longer under load.

**Why copy the whole repository into the image?** Not stated. My reading is that it is the simplest way to include the code and the committed dataset, at the cost of gaps 1 and 2 above.

---

## Outputs

| Output | Value |
|---|---|
| Generator images | `docker/statistical/Dockerfile`, `docker/ctgan/Dockerfile` (not built here) |
| Kubernetes Jobs | `k8s/jobs/statistical-job.yaml`, `k8s/jobs/ctgan-job.yaml` (not run here) |
| Dashboard | `dashboard/app.py`, `dashboard/requirements.txt`; run headless, no exceptions |
| Open problems | P-017 in [`problems_and_decisions.md`](problems_and_decisions.md) |
| Previous phase | [`D1_kubernetes_env_setup.md`](D1_kubernetes_env_setup.md) |
