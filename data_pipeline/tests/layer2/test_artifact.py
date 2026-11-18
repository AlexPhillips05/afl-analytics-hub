import pandas as pd
import pytest

from layer2.artifact import TrainedModel, load, save
from layer2.estimators import model_inputs, ridge
from tests.layer2.helpers import synthetic_features


def _model():
    f = synthetic_features()
    x = model_inputs(f, "ridge")
    est = ridge(10.0).fit(x, f["target_home_margin"])
    return f, TrainedModel(kind="ridge", estimator=est, feature_names=list(x.columns), scale=25.0,
                           elo_config_name="TUNED_CONFIG", trained_seasons=(2010, 2022), params={"alpha": 10.0})


def test_save_load_predict_round_trip(tmp_path):
    f, model = _model()
    path = tmp_path / "model.joblib"

    save(model, path)
    loaded = load(path)

    pd.testing.assert_frame_equal(loaded.predict(f), model.predict(f))
    assert list(model.predict(f).columns) == ["pred_home_margin", "pred_home_win_prob"]
    assert loaded.kind == "ridge" and loaded.scale == 25.0


def test_predict_names_missing_columns():
    f, model = _model()

    with pytest.raises(ValueError, match="form_margin_diff"):
        model.predict(f.drop(columns=["form_margin_diff"]))
