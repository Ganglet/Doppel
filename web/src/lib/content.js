// Static words. Every number on the page comes from data/dashboard.json, not from this file.

export const TRACKS = [
  { id: 't1', name: 'Track 1', role: 'Generative modeling', owner: 'Angshuman' },
  { id: 't2', name: 'Track 2', role: 'Evaluation', owner: 'Rayyan' },
  { id: 't3', name: 'Track 3', role: 'Data engineering', owner: 'Anoushka' },
  { id: 't4', name: 'Track 4', role: 'Systems and delivery', owner: 'Anshuman CE' },
]

export const ROADMAP = [
  {
    phase: 'Phase 1',
    weeks: 'Weeks 1-2',
    cells: {
      t1: ['done', 'Generator contract, shared codec, validator, statistical baseline, literature review, diffusion design'],
      t2: ['done', 'Evaluation protocol, utility task, literature survey'],
      t3: ['done', 'Cleaned dataset, schema, feature dictionary, patient-level split'],
      t4: ['done', 'Base image, Kubernetes namespace and smoke-test Job, draft contracts (no PR template)'],
    },
  },
  {
    phase: 'Phase 2',
    weeks: 'Weeks 3-7',
    cells: {
      t1: ['partial', 'CTGAN and TVAE, in-train model selection, 165-fit sweep. Diffusion model not built'],
      t2: ['done', 'Fidelity, utility and privacy code, runner, contract JSON'],
      t3: ['done', 'Dataset manifest, validation checks, preprocessing image and Job'],
      t4: ['partial', 'Images and Jobs for the statistical and CTGAN generators, dashboard scaffold. No evaluation Job'],
    },
  },
  {
    phase: 'Phase 3',
    weeks: 'Weeks 8-11',
    cells: {
      t1: ['none', 'Diffusion training and final tuning of all generators'],
      t2: ['done', 'Five generators x 20 seeds, calibrated attacks with a positive control, validated Pareto frontier. Rerun needed for diffusion'],
      t3: ['none', 'Evaluation-dataset versioning, end-to-end data-flow validation'],
      t4: ['partial', 'Results dashboard prototype (this site, built by Track 2). Pipeline wiring and end-to-end test not started'],
    },
  },
  {
    phase: 'Phase 4',
    weeks: 'Weeks 12-14',
    cells: {
      t1: ['none', 'Methodology and results report sections'],
      t2: ['none', 'Evaluation section, final tables and plots'],
      t3: ['none', 'Data and methodology appendix'],
      t4: ['none', 'Demo video, README polish, slides, report assembly'],
    },
  },
]

export const STATUS_LABEL = { done: 'Done', partial: 'Partly done', none: 'Not started' }

export const STEPS = [
  { n: 1, title: 'Prepare the data', text: 'Turn 100 MIMIC-III Demo patients into 129 clean hospital admissions, split by patient into 94 training and 35 held-out rows.', owner: 'Track 3', status: 'done' },
  { n: 2, title: 'Generate synthetic records', text: 'Each generator learns from the 94 training rows only and produces a synthetic table of the same shape.', owner: 'Track 1', status: 'partial' },
  { n: 3, title: 'Evaluate on one protocol', text: 'Score every generator for realism, usefulness and privacy, over 20 random seeds each, against fixed reference points.', owner: 'Track 2', status: 'done' },
  { n: 4, title: 'Compare and deliver', text: 'Show the trade-offs, run the pipeline in containers, and write it up.', owner: 'Track 4', status: 'partial' },
]

export const TERMS = [
  ['Fidelity', 'How close the synthetic table is to the real one, measured as the average Jensen-Shannon divergence over 52 columns. Lower is better.'],
  ['Utility', 'How well a model trained on synthetic data predicts in-hospital death on real held-out patients (AUROC, where 0.5 is guessing). Higher is better, and the real-data ceiling is the score of a model trained on real data.'],
  ['Membership attack', 'An attacker tries to tell which real records were used to train the generator. 0.5 means guessing, 1.0 means the attacker always wins. Lower is better for privacy.'],
  ['Worst case', 'The highest score among three membership attacks. The privacy score uses it, because a weak attack can make a leaky generator look safe.'],
  ['True-positive rate at 1% false alarms', 'How many training records the attacker identifies while wrongly accusing only 1% of unseen records. Pure guessing gives 0.01.'],
  ['Ceiling and floor', 'Reference generators that give the attacks a known best case (a generator that copies its training rows) and worst case (real rows it never saw).'],
  ['Positive control', 'A generator known to leak, used to check that the attacks can see a leak at all. Here it is TVAE.'],
  ['Seeds and ± values', 'Every generator is run 20 times with different random seeds. Dots show the mean and whiskers show one standard deviation.'],
  ['Pareto frontier', 'A generator is on the frontier if no other generator is at least as good on every measure and better on one. It shows trade-offs and does not rank generators.'],
  ['Training rows', 'Only 94 rows, against 110 modeled columns. With so little data a flexible generator can simply copy what it saw.'],
]

export const LIMITS = [
  ['The diffusion model does not exist yet.', 'Every comparison covers two of the three generator families the project set out to compare.'],
  ['The neural generators are untuned.', 'CTGAN and TVAE run at their initial 300-epoch defaults, and the next tuning sweep may change these results.'],
  ['The dataset is tiny.', '94 training rows and a 35-row held-out set with 6 positives. The 20 seeds vary the generators and not the patients.'],
  ['Utility differences are mostly noise.', 'Seed-to-seed spread is 0.09 to 0.20 AUROC, larger than most gaps between generators.'],
  ['The attack scores are proxies.', 'They come from generators fit on 47 rows, and a direct attack on the full-size generator has no valid non-members.'],
  ['The containers were never run.', 'The Docker images and Kubernetes Jobs exist as files, and six gaps were found by reading them against the code they run.'],
]

export const DOCS = [
  ['Full evaluation result', 'docs/full_evaluation_result.md', 'Five generators, every metric, significance tests'],
  ['Positive control result', 'docs/positive_control_result.md', 'The attacks against a generator that memorizes'],
  ['Pareto frontier result', 'docs/full_pareto_result.md', 'The frontier and how sensitive it is'],
  ['Evaluation protocol', 'eval_protocol.md', 'Formulas, thresholds and generator arms'],
  ['Literature survey', 'docs/membership_inference_survey.md', '18 checked sources on membership inference'],
  ['Generator sweep', 'docs/sweep_result.md', 'Track 1: memorization against fidelity'],
  ['Decisions and problems log', 'docs/problems_and_decisions.md', 'ADR-001 to 027 and P-001 to 018'],
  ['Project README', 'README.md', 'Status, architecture and how to run everything'],
]
