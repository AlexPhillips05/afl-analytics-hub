import numpy as np
import pandas as pd
import pytest

from layer2.artifact import TrainedModel, load, save
from layer2.calibration import win_prob
from layer2.estimators import ELO_COLUMNS, elo_baseline, model_inputs, ridge
from layer2.evaluate import TARGET
from tests.layer2.helpers import synthetic_features


def _ridge(f):
    x = model_inputs(f, "ridge")
    return ridge(10.0).fit(x, f[TARGET]), list(x.columns)


def _engine_model():
    f = synthetic_features()
    f["elo_home_win_prob"] = np.linspace(0.2, 0.8, len(f))
    est, names = _ridge(f)
    return f, TrainedModel(kind="ridge", estimator=est, feature_names=names, elo_config_name="TUNED_CONFIG",
                           trained_seasons=(2010, 2022), params={"alpha": 10.0})


def test_elo_engine_probability_round_trip(tmp_path):
    f, model = _engine_model()
    path = tmp_path / "model.joblib"

    save(model, path)
    loaded = load(path)

    out = loaded.predict(f)
    pd.testing.assert_frame_equal(out, model.predict(f))
    assert list(out.columns) == ["pred_home_margin", "pred_home_win_prob"]
    assert list(out["pred_home_win_prob"]) == list(f["elo_home_win_prob"])     # straight from the Elo engine
    assert loaded.kind == "ridge" and loaded.prob_source == "elo_engine"


def test_margin_curve_probability_from_a_different_model(tmp_path):
    f = synthetic_features()
    est, names = _ridge(f)
    base = elo_baseline().fit(f[ELO_COLUMNS], f[TARGET])
    model = TrainedModel(kind="ridge", estimator=est, feature_names=names, elo_config_name="TUNED_CONFIG",
                         trained_seasons=(2010, 2022), params={"alpha": 10.0}, prob_source="margin",
                         prob_kind="baseline", prob_estimator=base, prob_feature_names=ELO_COLUMNS, scale=25.0)
    save(model, tmp_path / "m.joblib")

    out = load(tmp_path / "m.joblib").predict(f)

    np.testing.assert_allclose(out["pred_home_win_prob"], win_prob(base.predict(f[ELO_COLUMNS]), 25.0))
    np.testing.assert_allclose(out["pred_home_margin"], est.predict(f[names].astype(float)))


def test_predict_names_missing_columns():
    f, model = _engine_model()

    with pytest.raises(ValueError, match="form_margin_diff"):
        model.predict(f.drop(columns=["form_margin_diff"]))
    with pytest.raises(ValueError, match="elo_home_win_prob"):
        model.predict(f.drop(columns=["elo_home_win_prob"]))
