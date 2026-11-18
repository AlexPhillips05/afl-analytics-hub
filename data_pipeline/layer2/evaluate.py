import numpy as np
import pandas as pd

from elo.evaluation import match_bits, tip_correct
from layer2.estimators import MAKERS, model_inputs

TARGET = "target_home_margin"
RESULT = "target_home_result"  # 1 / 0.5 / 0, used to fit the calibration scale
# A margin candidate must beat the baseline in CV by at least this many standard errors of the per-game paired
# difference in absolute error. Ties and noise-level wins go to the simpler model.
MIN_Z = 2.0


def out_of_fold(kind: str, params: dict, features: pd.DataFrame, folds) -> pd.Series:
    """Walk-forward predictions: each fold's model is trained only on earlier seasons."""
    preds = []
    for _season, train, val in folds:
        model = MAKERS[kind](**params)
        model.fit(model_inputs(features.loc[train], kind), features.loc[train, TARGET])
        preds.append(pd.Series(model.predict(model_inputs(features.loc[val], kind)), index=val))
    return pd.concat(preds)


def score(pred_margin: pd.Series, prob: np.ndarray, features: pd.DataFrame) -> dict:
    """MAE, tipping accuracy and bits per game for predictions indexed like `features`."""
    actual = features.loc[pred_margin.index, TARGET]
    # tip_correct / match_bits only compare home vs away score, so (margin, 0) is equivalent.
    pairs = list(zip(prob, actual))
    return {
        "games": len(actual),
        "mae": float(np.mean(np.abs(pred_margin.to_numpy() - actual.to_numpy()))),
        "tip_accuracy": float(np.mean([tip_correct(p, m, 0) for p, m in pairs])),
        "bits_per_game": float(np.mean([match_bits(p, m, 0) for p, m in pairs])),
    }


def best_params(kind: str, grid: list[dict], features: pd.DataFrame, folds) -> tuple[dict, pd.Series, float]:
    """Grid point with the lowest pooled out-of-fold MAE: (params, OOF predictions, CV MAE)."""
    best = None
    for params in grid:
        oof = out_of_fold(kind, params, features, folds)
        mae = float(np.mean(np.abs(oof - features.loc[oof.index, TARGET])))
        if best is None or mae < best[2]:
            best = (params, oof, mae)
    return best


def paired_mae_diff(candidate: pd.Series, baseline: pd.Series, features: pd.DataFrame) -> tuple[float, float]:
    """Mean and standard error of |candidate error| - |baseline error| over the same games (negative = candidate better)."""
    actual = features.loc[candidate.index, TARGET]
    diff = (candidate - actual).abs() - (baseline.loc[candidate.index] - actual).abs()
    return float(diff.mean()), float(diff.std(ddof=1) / np.sqrt(len(diff)))


def margin_cv_gate(candidate: pd.Series, baseline: pd.Series, features: pd.DataFrame, min_z: float = MIN_Z) -> bool:
    """CV: the candidate's out-of-fold predictions must beat the baseline's by at least min_z standard errors."""
    diff, se = paired_mae_diff(candidate, baseline, features)
    return diff < -min_z * se


def margin_gate(candidate: dict, baseline: dict) -> bool:
    """Holdout: a margin model must still beat the baseline on MAE."""
    return candidate["mae"] < baseline["mae"]


def prob_gate(challenger: dict, default: dict) -> bool:
    """A probability source must beat the default (the Elo engine) on bits (applied in CV and again on the holdout)."""
    return challenger["bits_per_game"] > default["bits_per_game"]
