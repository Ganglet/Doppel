"""Statistical baseline: Gaussian copula over empirical marginals, plus the independent-marginals floor."""

import numpy as np
import pandas as pd
from scipy.stats import norm

from .base import Generator
from .codec import KIND_BINARY, KIND_CATEGORICAL

EPS = 1e-6


class _Discrete:
    # Each level owns a slice of [0, 1] sized by its frequency; fitting draws uniformly inside the slice.
    def __init__(self, values: np.ndarray):
        counts = pd.Series(values).value_counts()
        self.levels = counts.index.to_numpy()
        p = counts.to_numpy() / counts.sum()
        self.upper = np.cumsum(p)
        self.lower = self.upper - p
        self.index = {v: k for k, v in enumerate(self.levels)}

    def to_normal(self, values: np.ndarray, rng: np.random.Generator) -> np.ndarray:
        k = np.array([self.index[v] for v in values])
        return norm.ppf(np.clip(rng.uniform(self.lower[k], self.upper[k]), EPS, 1 - EPS))

    def from_normal(self, z: np.ndarray) -> np.ndarray:
        k = np.searchsorted(self.upper, norm.cdf(z), side="right")
        return self.levels[np.minimum(k, len(self.levels) - 1)]


class _Continuous:
    def __init__(self, values: np.ndarray):
        self.sorted = np.sort(values.astype(float))

    def to_normal(self, values: np.ndarray, rng: np.random.Generator) -> np.ndarray:
        ranks = pd.Series(values).rank(method="average").to_numpy()
        return norm.ppf((ranks - 0.5) / len(values))

    def from_normal(self, z: np.ndarray) -> np.ndarray:
        return np.quantile(self.sorted, norm.cdf(z))


def ledoit_wolf_shrinkage(X: np.ndarray) -> float:
    """Shrinkage intensity toward a scaled identity (Ledoit & Wolf, 2004). X must be column-centred."""
    n, d = X.shape
    S = X.T @ X / n
    mu = np.trace(S) / d
    X2 = X ** 2
    beta = (np.sum(X2.T @ X2) / n - np.sum(S ** 2)) / (n * d)
    delta = (np.sum(S ** 2) - 2 * mu * np.trace(S) + d * mu ** 2) / d
    return 0.0 if delta == 0 else float(min(beta, delta) / delta)


class GaussianCopula(Generator):
    """With more modeled columns than training rows (d > n), the raw correlation matrix is singular,
    so it is shrunk toward the identity. Ledoit-Wolf picks the intensity unless one is given."""

    name = "gaussian_copula"

    def __init__(self, shrinkage: float | None = None):
        self.shrinkage = shrinkage

    def fit(self, frame, spec, rng):
        self.columns = list(spec)
        self.marginals = {
            c: (_Discrete if spec[c] in (KIND_CATEGORICAL, KIND_BINARY) else _Continuous)(frame[c].to_numpy())
            for c in self.columns
        }
        Z = np.column_stack([self.marginals[c].to_normal(frame[c].to_numpy(), rng) for c in self.columns])
        sd = Z.std(axis=0)
        Z = (Z - Z.mean(axis=0)) / np.where(sd > 0, sd, 1.0)

        self.fitted_shrinkage = ledoit_wolf_shrinkage(Z) if self.shrinkage is None else self.shrinkage
        cov = (1 - self.fitted_shrinkage) * (Z.T @ Z / len(Z)) + self.fitted_shrinkage * np.eye(Z.shape[1])
        d = np.sqrt(np.diag(cov))
        self.corr = cov / np.outer(d, d)
        return self

    def sample(self, n, rng):
        # Cholesky, not eigh: with d > n the shrunk matrix has d - (n - 1) identical eigenvalues, and eigh's
        # basis inside that subspace depends on the LAPACK build, so the same seed drew different rows under
        # different numpy versions (P-008, P-009). The Cholesky factor of a positive-definite matrix is unique.
        Z = rng.multivariate_normal(np.zeros(len(self.columns)), self.corr, size=n, method="cholesky")
        return pd.DataFrame({c: self.marginals[c].from_normal(Z[:, j]) for j, c in enumerate(self.columns)})

    def hyperparams(self):
        return {
            "shrinkage": "ledoit_wolf" if self.shrinkage is None else self.shrinkage,
            "fitted_shrinkage": round(self.fitted_shrinkage, 4),
        }


class IndependentMarginals(GaussianCopula):
    """Reference floor, not one of the three benchmarked families: exact marginals, zero dependence."""

    name = "independent_marginals"

    def __init__(self):
        super().__init__(shrinkage=1.0)

    def hyperparams(self):
        return {}
