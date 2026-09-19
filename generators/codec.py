"""Shared encoder/decoder between the real CSV and the modeling frame every generator trains on.

All generators fit on the same modeling frame and are decoded by this same code, so any difference
in the benchmark comes from the generator, not from preprocessing.
"""

import json
from collections import Counter

import numpy as np
import pandas as pd

from . import schema as S

KIND_CATEGORICAL = "categorical"
KIND_BINARY = "binary"
KIND_INTEGER = "integer"
KIND_CONTINUOUS = "continuous"

N_TAIL_COL = "n_tail_codes"


def code_col(code: str) -> str:
    return f"icd_{code}"


def miss_col(item_id: str) -> str:
    return f"miss_{item_id}"


class FrameCodec:
    """Real CSV <-> modeling frame.

    ICD-9 handling: the primary code is a categorical column. Secondary codes seen in at least
    `min_count` training admissions become multi-hot columns. The rest form a tail pool, and only
    their count per admission (`n_tail_codes`) is modeled. On decode, tail codes are drawn from the
    pool by training frequency, independently of the rest of the row, so rare code combinations
    (the re-identifying part) are never reproduced. `n_diagnoses` is derived, not generated.
    """

    def __init__(self, min_count: int = 5):
        self.min_count = min_count

    def fit(self, train: pd.DataFrame) -> "FrameCodec":
        self.columns = list(train.columns)

        codes = train[S.CODES_COL].map(json.loads)
        secondary = Counter(c for row in codes for c in row[1:])
        ranked = sorted(secondary.items(), key=lambda kv: (-kv[1], kv[0]))
        self.vocab = [c for c, n in ranked if n >= self.min_count]
        tail = [(c, n) for c, n in ranked if n < self.min_count]
        self.tail_codes = np.array([c for c, _ in tail], dtype=object)
        self.tail_weights = np.array([n for _, n in tail], dtype=float)

        self.nullable_labs = [i for i in S.lab_ids(train) if train[S.lab_pair(i)[0]].isna().any()]
        self.fill = {c: float(train[c].median()) for i in self.nullable_labs for c in S.lab_pair(i)}

        spec = {c: KIND_CATEGORICAL for c in S.CATEGORICAL}
        spec |= {c: KIND_BINARY for c in S.BINARY}
        spec |= {miss_col(i): KIND_BINARY for i in self.nullable_labs}
        spec |= {code_col(c): KIND_BINARY for c in self.vocab}
        spec |= {c: KIND_INTEGER for c in S.INTEGER + [N_TAIL_COL]}
        spec |= {c: KIND_CONTINUOUS for c in S.continuous_cols(train)}
        self.spec = spec

        encoded = self.encode(train)
        self.bounds = {
            c: (float(encoded[c].min()), float(encoded[c].max()))
            for c, kind in spec.items() if kind in (KIND_INTEGER, KIND_CONTINUOUS)
        }
        return self

    def encode(self, df: pd.DataFrame) -> pd.DataFrame:
        out = {c: df[c].astype(str) for c in S.CATEGORICAL}
        out |= {c: df[c].astype(int) for c in S.BINARY}
        out |= {miss_col(i): df[S.lab_pair(i)[0]].isna().astype(int) for i in self.nullable_labs}

        secondary = df[S.CODES_COL].map(lambda raw: set(json.loads(raw)[1:]))
        out |= {code_col(c): secondary.map(lambda s, c=c: int(c in s)) for c in self.vocab}
        vocab = set(self.vocab)
        out[N_TAIL_COL] = secondary.map(lambda s: len(s - vocab))
        out |= {c: df[c].astype(int) for c in S.INTEGER}

        out |= {c: df[c].fillna(self.fill[c]) if c in self.fill else df[c] for c in S.continuous_cols(df)}
        return pd.DataFrame(out, index=df.index)[list(self.spec)]

    def decode(self, frame: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
        frame = frame.reset_index(drop=True)
        n = len(frame)

        out = {
            S.ID_COLS[0]: S.SYNTH_SUBJECT_BASE + np.arange(n),
            S.ID_COLS[1]: S.SYNTH_HADM_BASE + np.arange(n),
            S.SPLIT_COL: np.full(n, S.SYNTH_SPLIT, dtype=object),
        }
        out |= {c: frame[c].astype(str).to_numpy() for c in S.CATEGORICAL}
        # Floats are thresholded so neural generators can emit probabilities.
        out |= {c: (frame[c].astype(float).to_numpy() >= 0.5).astype(int) for c in S.BINARY}
        out[S.AGE_FLAG_COL] = out[S.AGE_FLAG_COL].astype(bool)

        for c, (lo, hi) in self.bounds.items():
            v = np.clip(frame[c].astype(float).to_numpy(), lo, hi)
            out[c] = np.rint(v).astype(int) if self.spec[c] == KIND_INTEGER else v
        out[S.AGE_COL] = np.where(out[S.AGE_FLAG_COL], S.AGE_CAP, out[S.AGE_COL])

        for i in self.nullable_labs:
            missing = frame[miss_col(i)].astype(float).to_numpy() >= 0.5
            for c in S.lab_pair(i):
                out[c] = np.where(missing, np.nan, out[c])

        hits = frame[[code_col(c) for c in self.vocab]].astype(float).to_numpy() >= 0.5
        codes = [
            self._decode_codes(out[S.PRIMARY_COL][r], hits[r], out[N_TAIL_COL][r], rng)
            for r in range(n)
        ]
        out[S.CODES_COL] = [json.dumps(c) for c in codes]
        out[S.N_DIAG_COL] = np.array([len(c) for c in codes])

        return pd.DataFrame(out)[self.columns]

    def _decode_codes(self, primary: str, hit_row: np.ndarray, n_tail: int, rng: np.random.Generator) -> list[str]:
        # Code order after the primary is not modeled: vocab hits by train frequency, then tail draws.
        found = [c for c, hit in zip(self.vocab, hit_row) if hit and c != primary]
        taken = set(found) | {primary}
        pool = np.array([k for k, c in enumerate(self.tail_codes) if c not in taken], dtype=int)
        k = min(int(n_tail), len(pool))
        if k:
            w = self.tail_weights[pool]
            found += [str(c) for c in self.tail_codes[rng.choice(pool, size=k, replace=False, p=w / w.sum())]]
        return [str(primary)] + found

    def describe(self) -> dict:
        return {
            "min_count": self.min_count,
            "vocab_size": len(self.vocab),
            "tail_pool_size": len(self.tail_codes),
            "nullable_labs": self.nullable_labs,
            "modeled_columns": len(self.spec),
        }
