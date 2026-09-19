"""
Doppel - Track 2 evaluation runner.

Scores one synthetic dataset and writes results/<run_id>.json in the shape of
contracts/schemas/evaluation_result.schema.json.

    python -m evaluation.eval_runner --generator gaussian_copula --seed 42
"""

import argparse
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

from evaluation.attribute_inference import run_attribute_inference, run_attribute_targets
from evaluation.fidelity_metrics import run_fidelity_report
from generators import schema as S
from generators.codec import FrameCodec
from generators.generate import GENERATORS, run as run_generator
from evaluation.membership_inference import NUMERIC_COLS, codes_distances, gower_distances, run_membership_inference
from evaluation.utility_eval import utility_gap_report

N_SHADOW = 8

RESULTS_DIR = Path("results")
SCHEMA_PATH = Path("contracts/schemas/evaluation_result.schema.json")


def _plain(obj):
    if isinstance(obj, dict):
        return {str(k): _plain(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_plain(v) for v in obj]
    if isinstance(obj, (np.floating, float)):
        return None if np.isnan(obj) else float(obj)
    if isinstance(obj, np.integer):
        return int(obj)
    return obj


def load_synthetic(generator, seed):
    path = S.SYNTH_DIR / f"{generator}_seed{seed}.csv"
    if not path.exists():
        path = run_generator(generator, seed)
    return pd.read_csv(path)


def real_generator_fn(name, min_count=5):
    def generate(member_df, numeric_cols, n_samples, seed):
        fit_rng, sample_rng, decode_rng = (np.random.default_rng(s) for s in np.random.SeedSequence(seed).spawn(3))
        member_df = member_df.reset_index(drop=True)
        codec = FrameCodec(min_count=min_count).fit(member_df)
        model = GENERATORS[name]().fit(codec.encode(member_df), codec.spec, fit_rng)
        return codec.decode(model.sample(n_samples, sample_rng), decode_rng)

    return generate


def cached(generator_fn):
    memo = {}

    def generate(member_df, numeric_cols, n_samples, seed):
        key = (seed, n_samples, tuple(member_df.index))
        if key not in memo:
            memo[key] = generator_fn(member_df, numeric_cols, n_samples, seed)
        return memo[key]

    return generate


def evaluate(generator, seed):
    real = S.load_real()
    train = real[real[S.SPLIT_COL] == S.TRAIN_SPLIT].reset_index(drop=True)
    holdout = real[real[S.SPLIT_COL] != S.TRAIN_SPLIT].reset_index(drop=True)
    synth = load_synthetic(generator, seed)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        fidelity = run_fidelity_report(train, synth)
        utility = utility_gap_report(train, holdout, synth)
        attribute = run_attribute_inference(synth, holdout)
        attribute_targets = run_attribute_targets(synth, train, holdout)
        generator_fn = cached(real_generator_fn(generator))
        attacks = {
            "membership_inference": None,
            "membership_inference_gower": gower_distances,
            "membership_inference_codes": codes_distances,
        }
        membership = {
            name: {**run_membership_inference(
                train, generator_fn, NUMERIC_COLS, n_shadow=N_SHADOW, seed=seed, distance_fn=fn
            ), "n_shadow": N_SHADOW}
            for name, fn in attacks.items()
        }
        worst = max(membership, key=lambda k: membership[k]["mean_attack_auroc"])

    return {
        "run_id": f"{generator}_seed{seed}",
        "generator_name": generator,
        "metrics": _plain({
            "fidelity": fidelity,
            "utility": utility,
            "privacy": {
                "attribute_inference": attribute,
                "attribute_inference_targets": attribute_targets,
                **membership,
                "membership_worst_case": {
                    "attack": worst,
                    "mean_attack_auroc": membership[worst]["mean_attack_auroc"],
                },
            },
        }),
    }


def validate_result(result):
    import jsonschema

    jsonschema.validate(result, json.loads(SCHEMA_PATH.read_text()))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--generator", required=True)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args(argv)

    result = evaluate(args.generator, args.seed)
    validate_result(result)

    RESULTS_DIR.mkdir(exist_ok=True)
    path = RESULTS_DIR / f"{result['run_id']}.json"
    path.write_text(json.dumps(result, indent=2) + "\n")
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
