"""Stage 2 entry point: fit one generator on the train split, sample, decode, validate, write.

    python -m generators.generate --generator gaussian_copula --seed 42
    python -m generators.generate --generator ctgan --seed 42 --param epochs=1000

Writes <out-dir>/<generator>_seed<seed>.csv plus a .manifest.json sidecar that conforms to
contracts/schemas/generator_output.schema.json. Nothing is written if the output fails the contract,
so a downstream stage never picks up an invalid file.
"""

import argparse
import hashlib
import importlib
import json
import subprocess
import sys
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from . import __version__
from . import schema as S
from .codec import FrameCodec
from .validate import check_contract

class _LazyRegistry(Mapping):
    """name -> Generator class, importing each module on first access so the copula image never needs torch.

    Indexing returns the class, as the Phase 1 registry did. Track 2's eval_runner calls GENERATORS[name]().
    """

    def __init__(self, paths: dict[str, str]):
        self._paths = paths

    def __getitem__(self, name: str) -> type:
        module, cls = self._paths[name].split(":")
        return getattr(importlib.import_module(f"{__package__}.{module}"), cls)

    def __iter__(self):
        return iter(self._paths)

    def __len__(self):
        return len(self._paths)


GENERATORS = _LazyRegistry({
    "gaussian_copula": "copula:GaussianCopula",
    "independent_marginals": "copula:IndependentMarginals",
    "ctgan": "ctgan_tvae:CTGAN",
    "tvae": "ctgan_tvae:TVAE",
})


def load_generator(name: str) -> type:
    return GENERATORS[name]


def synthesize(train: pd.DataFrame, generator: str, seed: int, params: dict | None = None,
               n_rows: int | None = None, min_count: int = 5):
    """Fit on `train`, sample, decode. Returns (codec, fitted model, synthetic frame in the real CSV's schema)."""
    fit_rng, sample_rng, decode_rng = (np.random.default_rng(s) for s in np.random.SeedSequence(seed).spawn(3))
    codec = FrameCodec(min_count=min_count).fit(train)
    model = load_generator(generator)(**(params or {})).fit(codec.encode(train), codec.spec, fit_rng)
    synth = codec.decode(model.sample(n_rows or len(train), sample_rng), decode_rng)
    return codec, model, synth


def _git_commit() -> str:
    try:
        sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
        dirty = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, check=True).stdout.strip()
        return sha + ("-dirty" if dirty else "")
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def run(generator: str, seed: int, params: dict | None = None, n_rows: int | None = None, min_count: int = 5,
        real_csv: Path = S.REAL_CSV, out_dir: Path = S.SYNTH_DIR) -> Path:
    real = S.load_real(real_csv)
    train = real[real[S.SPLIT_COL] == S.TRAIN_SPLIT].reset_index(drop=True)
    codec, model, synth = synthesize(train, generator, seed, params, n_rows, min_count)

    if errors := check_contract(synth, real):
        raise ValueError("output violates the Stage 2 contract:\n  - " + "\n  - ".join(errors))

    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{generator}_seed{seed}.csv"
    synth.to_csv(path, index=False)

    created = datetime.now(timezone.utc)
    train_sha = hashlib.sha256(Path(real_csv).read_bytes()).hexdigest()
    manifest = {
        "run_id": f"{generator}_seed{seed}_{created:%Y%m%dT%H%M%SZ}",
        "generator_name": generator,
        "generator_version": __version__,
        "input_dataset_id": f"{Path(real_csv).stem}@{train_sha[:12]}",
        "output_path": str(path),
        "output_format": "csv",
        "num_records": len(synth),
        "seed": seed,
        "hyperparams": model.hyperparams(),
        "train_rows": len(train),
        "train_csv_sha256": train_sha,
        "codec": codec.describe(),
        "git_commit": _git_commit(),
        "created_utc": created.isoformat(timespec="seconds"),
    }
    path.with_suffix(".manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return path


def _param(text: str) -> tuple[str, object]:
    key, sep, value = text.partition("=")
    if not sep:
        raise argparse.ArgumentTypeError(f"expected key=value, got {text!r}")
    try:
        return key, json.loads(value)
    except json.JSONDecodeError:
        return key, value


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--generator", required=True, choices=sorted(GENERATORS))
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--param", type=_param, action="append", default=[], metavar="KEY=VALUE",
                        help="generator hyperparameter, value parsed as JSON when possible (repeatable)")
    parser.add_argument("--n-rows", type=int, default=None, help="default: size of the train split")
    parser.add_argument("--min-count", type=int, default=5, help="min train admissions for a code to be multi-hot")
    parser.add_argument("--real-csv", type=Path, default=S.REAL_CSV)
    parser.add_argument("--out-dir", type=Path, default=S.SYNTH_DIR)
    args = parser.parse_args(argv)

    try:
        path = run(args.generator, args.seed, dict(args.param), args.n_rows, args.min_count, args.real_csv, args.out_dir)
    except ValueError as e:
        print(f"FAIL  {e}", file=sys.stderr)
        return 1
    print(f"PASS  wrote {path} and {path.with_suffix('.manifest.json').name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
