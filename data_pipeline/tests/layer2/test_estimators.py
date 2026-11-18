import numpy as np

from layer2.estimators import ELO_COLUMNS, model_inputs, ridge, xgb
from tests.layer2.helpers import synthetic_features


def test_baseline_inputs_are_only_the_elo_columns():
    f = synthetic_features()

    assert list(model_inputs(f, "baseline").columns) == ELO_COLUMNS
    assert "form_margin_diff" in model_inputs(f, "ridge").columns


def test_inputs_are_float_including_booleans():
    x = model_inputs(synthetic_features(), "ridge")

    assert all(dtype == np.float64 for dtype in x.dtypes)


def test_ridge_handles_missing_values():
    f = synthetic_features()
    x = model_inputs(f, "ridge")
    assert x.isna().any().any()

    model = ridge(10.0).fit(x, f["target_home_margin"])

    assert np.isfinite(model.predict(x)).all()


def test_xgboost_is_deterministic():
    f = synthetic_features()
    x, y = model_inputs(f, "xgboost"), f["target_home_margin"]

    a = xgb(max_depth=2, learning_rate=0.1, n_estimators=50, min_child_weight=5).fit(x, y).predict(x)
    b = xgb(max_depth=2, learning_rate=0.1, n_estimators=50, min_child_weight=5).fit(x, y).predict(x)

    assert np.array_equal(a, b)
