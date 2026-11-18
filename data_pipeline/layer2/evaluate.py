import numpy as np
import pandas as pd

from elo.evaluation import match_bits, tip_correct
from layer2.estimators import MAKERS, model_inputs

TARGET = "target_home_margin"
RESULT = "target_home_result"  # 1 / 0.5 / 0, used to fit the calibration scale


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


def cv_gate(candidate: dict, baseline: dict) -> bool:
    """Candidate must beat the baseline on MAE without being worse on bits."""
    return candidate["mae"] < baseline["mae"] and candidate["bits_per_game"] >= baseline["bits_per_game"]


def holdout_verdict(passed_cv: bool, candidate: dict, baseline: dict) -> str:
    if passed_cv and cv_gate(candidate, baseline):
        return "ADOPT"
    return "KEEP ELO BASELINE"
