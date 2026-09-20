"""Memorization check for model selection: distance to closest record (DCR), computed inside train only.

The holdout belongs to Track 2's evaluation (ADR-001), so model selection never touches it. Instead, train
is split by patient into a fit part and a reference part. Rows from a generator fitted on the fit part
should sit about as far from the fit rows as the reference rows (real, but unseen) do.

    dcr_ratio       median DCR(synthetic -> fit) / median DCR(reference -> fit)
                    ~1: as novel as unseen real rows; < 1: copying; > 1: further than real data sits
    near_copy_rate  share of synthetic rows closer to the fit set than the 5th percentile of reference
                    DCRs; ~0.05 for a generator that isn't copying

Distance is Gower (1971) on the modeling frame: range-scaled L1 on numeric columns, mismatch on discrete
ones, averaged over all columns.
"""

import numpy as np
import pandas as pd

from . import schema as S
from .codec import KIND_CONTINUOUS, KIND_INTEGER, FrameCodec

# Fixed, so every generator and seed is scored on the same folds.
FOLD_SEED = 0


def patient_folds(train: pd.DataFrame, k: int = 5, seed: int = FOLD_SEED):
    """Yield (fit, reference) splits of train, grouped by patient like ADR-001's split."""
    subjects = np.sort(train[S.ID_COLS[0]].unique())
    np.random.default_rng(seed).shuffle(subjects)
    for group in np.array_split(subjects, k):
        is_ref = train[S.ID_COLS[0]].isin(group)
        yield train[~is_ref].reset_index(drop=True), train[is_ref].reset_index(drop=True)


def _nearest_gower(query: pd.DataFrame, target: pd.DataFrame, numeric: list[str], discrete: list[str],
                   scale: np.ndarray) -> np.ndarray:
    qn = query[numeric].to_numpy(float) / scale
    tn = target[numeric].to_numpy(float) / scale
    d = np.abs(qn[:, None, :] - tn[None, :, :]).sum(-1)
    qd = query[discrete].astype(str).to_numpy()
    td = target[discrete].astype(str).to_numpy()
    d += (qd[:, None, :] != td[None, :, :]).sum(-1)
    return d.min(axis=1) / (len(numeric) + len(discrete))


def dcr_distances(fit: pd.DataFrame, ref: pd.DataFrame, synth: pd.DataFrame, min_count: int = 5):
    """Nearest-record distance to `fit` for each synthetic row and each reference row."""
    codec = FrameCodec(min_count).fit(fit)
    numeric = [c for c, kind in codec.spec.items() if kind in (KIND_INTEGER, KIND_CONTINUOUS)]
    discrete = [c for c in codec.spec if c not in numeric]

    fit_f, ref_f, syn_f = (codec.encode(df) for df in (fit, ref, synth))
    fill = fit_f[numeric].median()
    ref_f, syn_f = ref_f.fillna(fill), syn_f.fillna(fill)  # ref can miss a lab that fit never misses
    scale = (fit_f[numeric].max() - fit_f[numeric].min()).replace(0, 1).to_numpy(float)

    return (_nearest_gower(syn_f, fit_f, numeric, discrete, scale),
            _nearest_gower(ref_f, fit_f, numeric, discrete, scale))


def dcr_summary(synth_d: np.ndarray, ref_d: np.ndarray) -> dict:
    return {
        "dcr_ratio": float(np.median(synth_d) / np.median(ref_d)),
        "near_copy_rate": float(np.mean(synth_d < np.percentile(ref_d, 5))),
    }
