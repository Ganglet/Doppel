"""Stage 2 entry point: fit one generator on the train split, sample, decode, validate, write.

    python -m generators.generate --generator gaussian_copula --seed 42

Writes output/synthetic/<generator>_seed<seed>.csv plus a .manifest.json sidecar. Nothing is written
if the output fails the contract, so a downstream stage never picks up an invalid file.
"""

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from . import schema as S
from .codec import FrameCodec
from .copula import GaussianCopula, IndependentMarginals
from .validate import check_contract

GENERATORS = {g.name: g for g in (GaussianCopula, IndependentMarginals)}


def _git_commit() -> str:
    try:
        sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
        dirty = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, check=True).stdout.strip()
        return sha + ("-dirty" if dirty else "")
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def run(generator: str, seed: int, n_rows: int | None = None, min_count: int = 5, out_dir: Path = S.SYNTH_DIR) -> Path:
    real = S.load_real()
    train = real[real[S.SPLIT_COL] == S.TRAIN_SPLIT].reset_index(drop=True)
    fit_rng, sample_rng, decode_rng = (np.random.default_rng(s) for s in np.random.SeedSequence(seed).spawn(3))

    codec = FrameCodec(min_count=min_count).fit(train)
    model = GENERATORS[generator]().fit(codec.encode(train), codec.spec, fit_rng)
    n = n_rows or len(train)
    synth = codec.decode(model.sample(n, sample_rng), decode_rng)

    if errors := check_contract(synth, real):
        raise ValueError("output violates the Stage 2 contract:\n  - " + "\n  - ".join(errors))

    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{generator}_seed{seed}.csv"
    synth.to_csv(path, index=False)
    manifest = {
        "generator": generator,
        "hyperparams": model.hyperparams(),
        "seed": seed,
        "n_rows": n,
        "train_rows": len(train),
        "train_csv": str(S.REAL_CSV),
        "train_csv_sha256": hashlib.sha256(S.REAL_CSV.read_bytes()).hexdigest(),
        "codec": codec.describe(),
        "git_commit": _git_commit(),
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    path.with_suffix(".manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return path


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--generator", required=True, choices=sorted(GENERATORS))
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--n-rows", type=int, default=None, help="default: size of the train split")
    parser.add_argument("--min-count", type=int, default=5, help="min train admissions for a code to be multi-hot")
    args = parser.parse_args(argv)

    try:
        path = run(args.generator, args.seed, args.n_rows, args.min_count)
    except ValueError as e:
        print(f"FAIL  {e}", file=sys.stderr)
        return 1
    print(f"PASS  wrote {path} and {path.with_suffix('.manifest.json').name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
