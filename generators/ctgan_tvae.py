"""GAN-family arm: CTGAN and TVAE (Xu et al., 2019) from the `ctgan` library, run on the shared modeling frame.

I call `ctgan` directly rather than SDV's synthesizer wrappers. SDV re-detects column types and applies
its own transforms, which would stack a second preprocessing layer on top of the shared codec (ADR-008).
The mode-specific normalization inside CTGAN/TVAE is part of the method itself, so it stays.

On 94 rows one epoch is a single gradient step (steps per epoch = max(n // batch_size, 1)), so `epochs`
is effectively the step count and the main hyperparameter.
"""

import numpy as np
import pandas as pd
import torch
from ctgan import CTGAN as _CTGAN
from ctgan import TVAE as _TVAE

from .base import Generator
from .codec import KIND_BINARY, KIND_CATEGORICAL

# One thread is 1.5-2x faster than eight on matrices this small (profiled), and a fixed thread count
# keeps float reduction order, and so the output, identical across machines.
TORCH_THREADS = 1


class _CtganLibraryModel(Generator):
    model_cls: type
    defaults: dict

    def __init__(self, **params):
        self.params = {**self.defaults, **params}

    def fit(self, frame: pd.DataFrame, spec: dict[str, str], rng: np.random.Generator):
        self.columns = list(spec)
        discrete = [c for c, kind in spec.items() if kind in (KIND_CATEGORICAL, KIND_BINARY)]
        # CPU only: 94 rows gain nothing from a GPU, and CPU keeps runs reproducible from the seed.
        torch.set_num_threads(TORCH_THREADS)
        self.model = self.model_cls(enable_gpu=False, **self.params)
        self.model.set_random_state(int(rng.integers(2**31)))
        self.model.fit(frame, discrete_columns=discrete)
        return self

    def sample(self, n: int, rng: np.random.Generator) -> pd.DataFrame:
        torch.set_num_threads(TORCH_THREADS)
        self.model.set_random_state(int(rng.integers(2**31)))
        return self.model.sample(n)[self.columns]

    def hyperparams(self) -> dict:
        return dict(self.params)


class CTGAN(_CtganLibraryModel):
    name = "ctgan"
    model_cls = _CTGAN
    defaults = {"epochs": 300, "batch_size": 500, "pac": 10}


class TVAE(_CtganLibraryModel):
    name = "tvae"
    model_cls = _TVAE
    defaults = {"epochs": 300, "batch_size": 500}
