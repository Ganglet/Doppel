"""The interface every Doppel generator implements."""

from abc import ABC, abstractmethod

import numpy as np
import pandas as pd


class Generator(ABC):
    """Fits on the codec's modeling frame and samples frames of the same shape.

    `sample` must return exactly the columns of `spec`, in order, with no NaN (missingness is carried
    by the `miss_*` columns). Categorical values must come from the levels seen in `fit`. Binary
    columns may be 0/1 or probabilities; the codec thresholds them at 0.5.

    Randomness comes only from the `rng` arguments, so a run is reproducible from its seed. Torch-based
    generators should seed torch from `rng.integers(2**31)`.
    """

    name: str

    @abstractmethod
    def fit(self, frame: pd.DataFrame, spec: dict[str, str], rng: np.random.Generator) -> "Generator":
        ...

    @abstractmethod
    def sample(self, n: int, rng: np.random.Generator) -> pd.DataFrame:
        ...

    def hyperparams(self) -> dict:
        return {}
