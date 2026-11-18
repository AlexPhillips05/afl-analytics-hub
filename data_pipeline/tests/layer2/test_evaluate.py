import math

import numpy as np
import pandas as pd
import pytest

from layer2.evaluate import margin_cv_gate, margin_gate, out_of_fold, paired_mae_diff, prob_gate, score
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


def test_paired_mae_diff():
    f = pd.DataFrame({"target_home_margin": [0, 0, 0, 0]})
    base = pd.Series([10.0, -10.0, 10.0, 10.0], index=f.index)
    cand = pd.Series([9.0, -11.0, 9.0, 10.5], index=f.index)

    diff, se = paired_mae_diff(cand, base, f)

    d = np.array([-1.0, 1.0, -1.0, 0.5])                       # |cand error| - |base error| per game
    assert diff == pytest.approx(d.mean())
    assert se == pytest.approx(d.std(ddof=1) / 2)


def test_margin_cv_gate_needs_a_clear_win():
    f = pd.DataFrame({"target_home_margin": [0, 0, 0, 0]})
    base = pd.Series([10.0, 10.0, 10.0, 10.0], index=f.index)

    assert margin_cv_gate(pd.Series([2.0, 3.0, 2.0, 3.0], index=f.index), base, f)          # far better every game
    assert not margin_cv_gate(pd.Series([9.0, 11.0, 9.0, 10.5], index=f.index), base, f)    # lower on average, but noise
    assert not margin_cv_gate(base.copy(), base, f)                                         # a tie goes to the baseline


@pytest.mark.parametrize("cand, base, expected", [
    ({"mae": 29.0, "bits_per_game": 0.10}, {"mae": 30.0, "bits_per_game": 0.19}, True),    # bits don't matter
    ({"mae": 30.0, "bits_per_game": 0.25}, {"mae": 30.0, "bits_per_game": 0.19}, False),   # must beat MAE
    ({"mae": 31.0, "bits_per_game": 0.25}, {"mae": 30.0, "bits_per_game": 0.19}, False),
])
def test_holdout_margin_gate_is_mae_only(cand, base, expected):
    assert margin_gate(cand, base) is expected


@pytest.mark.parametrize("chal, default, expected", [
    ({"mae": 99.0, "bits_per_game": 0.20}, {"mae": None, "bits_per_game": 0.19}, True),    # MAE doesn't matter
    ({"mae": 20.0, "bits_per_game": 0.19}, {"mae": None, "bits_per_game": 0.19}, False),   # must be strictly better
    ({"mae": 20.0, "bits_per_game": 0.18}, {"mae": None, "bits_per_game": 0.19}, False),
])
def test_prob_gate_is_bits_only(chal, default, expected):
    assert prob_gate(chal, default) is expected
