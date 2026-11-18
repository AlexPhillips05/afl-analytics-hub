import itertools

import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBRegressor

from features.build import feature_columns

ELO_COLUMNS = ["elo_diff", "vai_diff"]

RIDGE_GRID = [{"alpha": a} for a in (0.1, 1.0, 10.0, 100.0, 1000.0)]
XGB_GRID = [
    {"max_depth": d, "learning_rate": lr, "n_estimators": n, "min_child_weight": w}
    for d, lr, n, w in itertools.product((2, 3, 4), (0.03, 0.1), (100, 300, 600), (5, 20))
]


def elo_baseline():
    return LinearRegression()


def ridge(alpha: float):
    # Empty first-game rest/form values become 0 ("no difference") before scaling.
    return make_pipeline(SimpleImputer(strategy="constant", fill_value=0.0), StandardScaler(), Ridge(alpha=alpha))


def xgb(**params):
    return XGBRegressor(objective="reg:squarederror", subsample=0.8, colsample_bytree=0.8,
                        random_state=0, n_jobs=4, **params)  # 4 threads: ~13x faster than all cores on this tiny data


MAKERS = {"baseline": lambda **_: elo_baseline(), "ridge": ridge, "xgboost": xgb}


def model_inputs(features: pd.DataFrame, kind: str) -> pd.DataFrame:
    """Input matrix for a model kind: the baseline sees only the Elo columns; others see every feature."""
    columns = ELO_COLUMNS if kind == "baseline" else feature_columns(features)
    return features[columns].astype(float)
