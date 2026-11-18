import numpy as np
from scipy.optimize import minimize_scalar


def win_prob(pred_margin, s: float) -> np.ndarray:
    """P(home win) from a predicted home margin: logistic with scale s (points)."""
    return 1.0 / (1.0 + np.exp(-np.asarray(pred_margin, dtype=float) / s))


def fit_scale(pred_margin, result) -> float:
    """Maximum-likelihood logistic scale s; result is 1 / 0.5 / 0 (draws as half a win)."""
    pred, y = np.asarray(pred_margin, dtype=float), np.asarray(result, dtype=float)

    def neg_log_likelihood(log_s: float) -> float:
        p = np.clip(win_prob(pred, np.exp(log_s)), 1e-12, 1 - 1e-12)
        return -np.sum(y * np.log(p) + (1 - y) * np.log(1 - p))

    best = minimize_scalar(neg_log_likelihood, bounds=(np.log(1.0), np.log(500.0)), method="bounded")
    return float(np.exp(best.x))
