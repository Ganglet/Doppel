# Kubernetes Environment and Integration Contracts

**Phase:** Phase 1 — Foundation & Design (Weeks 1–2), commits `9cecc0a` (2026-09-18) and `a5cf30e` (2026-09-19), branch `track4-phase1-kubernetes_env_setup`, merged as PRs #2 and #5
**Owner:** Anshuman CE (Track 4 / Track D). Written up by Rayyan (Track 2) from the repository and the checks below; not yet reviewed by the owner
**Status:** Delivered as files. All three contract schemas are in use, and all 100 generator manifests and all 100 evaluation results validate against theirs. The Docker image and Kubernetes objects were checked statically only: the Docker daemon was not running where this was written and no cluster was up, so none of it has been run here. No PR template exists, and the repo shows no record of a minikube or kind run.

---

## Objective

Give all four tracks one shared environment and one set of interface contracts before anyone's code depends on the others, so that a generator, an evaluator and a preprocessing step can be run and chained the same way by everyone. The blueprint asks for this in Phase 1 because the contracts have to exist before the code that must satisfy them.

---

## What was built

### 1. Base image

`docker/base/Dockerfile` builds `doppel/base:0.1` from `python:3.11-slim`, installs `curl`, installs the root `requirements.txt` (the first version installed unpinned `numpy` and `pandas`; commit `a5cf30e`, "pinned requirements.txt to docker image", switched it to the pinned file), and copies in a smoke-test program whose default command prints the Python version, platform and project name. Later images build on it: `docker/preprocessing` uses it as its parent, so it must be built first.

### 2. Namespace and smoke-test Job

`k8s/namespace/namespace.yaml` defines the namespace `doppel`. `k8s/jobs/smoke-test-job.yaml` runs `doppel/base:0.1` as the Job `doppel-smoke-test` there, with `backoffLimit: 1`, `restartPolicy: Never`, `imagePullPolicy: IfNotPresent` and one environment variable. Its purpose is to prove that an image built locally can be scheduled and run.

### 3. Integration contracts

[`contracts/README.md`](../contracts/README.md) records the intended data directories, which track produces and consumes what, and the file formats (CSV for tables, JSON for metadata and results). Three JSON schemas define the artifacts that pass between stages.

| Schema | Required fields | Notes |
|---|---|---|
| `dataset.schema.json` | `dataset_id`, `schema_version`, `data_path`, `format`, `columns` | Track 3's manifest conforms to it, and `validate_dataset.py` enforces it |
| `generator_output.schema.json` | `run_id`, `generator_name`, `generator_version`, `input_dataset_id`, `output_path`, `output_format`, `num_records`, `seed` | Amended after Track 1's review (2026-09-19): `generator_name` is an enum of the real generators including `tabular_diffusion`, and `seed` is required |
| `evaluation_result.schema.json` | `run_id`, `generator_name`, `metrics` | `metrics` may contain only `fidelity`, `utility` and `privacy`, each a free-form object, so the schema fixes the shape but not the contents |

Two later sections of the contracts README record decisions: §5 (Track 1's review, 2026-09-19) and §6 (the Track 3 and Track 4 path decision, 2026-09-20), which moved the processed dataset from the draft's `data/processed/` to `output/mimic_demo_clean.csv`.

### Checks I ran

| Check | Result |
|---|---|
| Generator manifests vs `generator_output.schema.json` | 100 of 100 validate |
| Evaluation results vs `evaluation_result.schema.json` | 100 of 100 validate |
| Dataset manifest via `validate_dataset.py` | passes |
| Kubernetes YAML parses | all 5 files parse (namespace and 4 Jobs) |
| `kubectl apply --dry-run=client` | not possible, it needed the API server and no cluster was running |
| `docker build`, `kubectl apply`, a smoke-test Job run | not run, the Docker daemon was not running |

### Not done

- **No PR template** (a blueprint Phase 1 task). The branch naming convention is recorded as ADR-006 in [`problems_and_decisions.md`](problems_and_decisions.md), which was written by Track 2.
- **No record of the environment running.** A `minikube` kubectl context exists on the machine where this was written, but no cluster was running and nothing in the repository shows a smoke-test result.
- **The `evaluation_result` schema is loose.** It can't reject a result with the wrong or missing metrics, because the three metric objects are unconstrained.
- **Contract §1 is partly out of date.** It still lists `data/...` paths that §6 replaced, so a reader who stops at §1 gets the wrong layout.

---

## Commands

```bash
# Verify the contracts against real output (verified 2026-09-24)
python validate_dataset.py                                             # dataset manifest vs dataset.schema.json
python -m generators.generate --generator gaussian_copula --seed 42    # writes a manifest checked against generator_output.schema.json
python -m evaluation.eval_runner --generator gaussian_copula --seed 42 # validates the result against evaluation_result.schema.json before writing

# Build and run the environment (follows the files; NOT run here)
docker build -f docker/base/Dockerfile -t doppel/base:0.1 .
kubectl apply -f k8s/namespace/namespace.yaml
kubectl apply -f k8s/jobs/smoke-test-job.yaml
kubectl logs -n doppel job/doppel-smoke-test
```

Expected from the smoke Job, per `docker/smoke-test/app.py`: the Python version, the platform, `Project: Doppel` and `Smoke test completed successfully.`

---

## Key Decisions

**Why contracts before code?** The contracts README says all tracks "must review and approve the final schemas before implementation", and the blueprint's Phase 1 task for this track is to draft them before code is written.

**Why is `generator_output` strict about extra fields?** The schema sets `additionalProperties: false`, and Track 1's review (§5) kept that while declaring the fields Track 1's manifests actually write, so a manifest with an unknown field is rejected instead of silently accepted.

**Why pin `requirements.txt` into the image?** Commit `a5cf30e` replaced the unpinned install with the pinned file. ADR-023 gives the related reason for a single environment: "one pipeline should run on one environment", so Track 1 dropped its own numpy 2.5.3 pins, which needed Python 3.12. Track 2 separately found the copula's output depended on the numpy build (P-008, P-009), which is the failure pinning prevents.

**Why `imagePullPolicy: IfNotPresent`?** My reading, not stated in the repo: the images are built locally and not pushed to a registry, so the cluster has to use what is already present.

**Why is the `evaluation_result` schema loose?** Not stated in the repo. My reading is that the metric set was not settled in Phase 1, before Track 2's protocol existed.

---

## Outputs

| Output | Value |
|---|---|
| Base image | `docker/base/Dockerfile` → `doppel/base:0.1` |
| Namespace | `doppel` (`k8s/namespace/namespace.yaml`) |
| Smoke-test Job | `doppel-smoke-test` (`k8s/jobs/smoke-test-job.yaml`) |
| Contracts | `contracts/README.md`, `contracts/schemas/{dataset,generator_output,evaluation_result}.schema.json` |
| Contract conformance | 100/100 generator manifests, 100/100 evaluation results, dataset manifest passes |
| Next phase | [`D2_system_integration.md`](D2_system_integration.md) |
