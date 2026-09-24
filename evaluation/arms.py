"""Named generator configurations Track 2 evaluates. Each arm is (generator name, hyperparameters)."""

ARMS = {
    "independent_marginals": ("independent_marginals", {}),
    "gaussian_copula": ("gaussian_copula", {}),
    "gaussian_copula_shrink025": ("gaussian_copula", {"shrinkage": 0.25}),  # config Track 1 carried into Phase 3 (ADR-024)
    "ctgan": ("ctgan", {}),  # 300 epochs, the least-bad CTGAN config (ADR-024)
    "tvae": ("tvae", {}),  # 300 epochs; memorizes, so it is the membership-attack positive control (ADR-024)
}


def resolve(arm):
    return ARMS.get(arm, (arm, {}))
