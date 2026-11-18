import math

import numpy as np
import pandas as pd
import pytest

from layer2.evaluate import cv_gate, holdout_verdict, out_of_fold, score
from layer2.splits import walk_forward_folds
from tests.layer2.helpers import synthetic_features


def test_score_maths():
    f = pd.DataFrame({"target_home_margin": [10, -20, 0]})
    pred = pd.Series([4.0, -10.0, 3.0], index=f.index)
    prob = np.array([0.75, 0.4, 0.6])

    s = score(pred, prob, f)

    assert s["games"] == 3
    assert s["mae"] == pytest.approx((6 + 10 + 3) / 3)
    assert s["tip_accuracy"] == pytest.approx(1.0)      # home win tipped home, away win tipped away, draw counts
    assert s["bits_per_game"] == pytest.approx(
        ((1 + math.log2(0.75)) + (1 + math.log2(0.6)) + (1 + 0.5 * math.log2(0.6 * 0.4))) / 3)


def test_ridge_beats_baseline_when_a_non_elo_feature_matters():
    f = synthetic_features()
    folds = walk_forward_folds(f)

    def cv_mae(kind, params):
        oof = out_of_fold(kind, params, f, folds)
        return np.mean(np.abs(oof - f.loc[oof.index, "target_home_margin"]))

    assert cv_mae("ridge", {"alpha": 1.0}) < cv_mae("baseline", {})


def test_out_of_fold_predicts_each_validation_row_once():
    f = synthetic_features()
    folds = walk_forward_folds(f)

    oof = out_of_fold("baseline", {}, f, folds)

    assert oof.index.is_unique
    assert set(oof.index) == set().union(*(set(val) for _, _, val in folds))


@pytest.mark.parametrize("cand, base, expected", [
    ({"mae": 29.0, "bits_per_game": 0.20}, {"mae": 30.0, "bits_per_game": 0.19}, True),
    ({"mae": 29.0, "bits_per_game": 0.19}, {"mae": 30.0, "bits_per_game": 0.19}, True),    # equal bits is fine
    ({"mae": 29.0, "bits_per_game": 0.18}, {"mae": 30.0, "bits_per_game": 0.19}, False),   # bits guard
    ({"mae": 30.0, "bits_per_game": 0.25}, {"mae": 30.0, "bits_per_game": 0.19}, False),   # must beat MAE
])
def test_cv_gate(cand, base, expected):
    assert cv_gate(cand, base) is expected


def test_holdout_verdict_needs_cv_pass_and_holdout_win():
    better, worse = {"mae": 29.0, "bits_per_game": 0.2}, {"mae": 30.0, "bits_per_game": 0.2}

    assert holdout_verdict(True, better, worse) == "ADOPT"
    assert holdout_verdict(False, better, worse) == "KEEP ELO BASELINE"
    assert holdout_verdict(True, worse, better) == "KEEP ELO BASELINE"
