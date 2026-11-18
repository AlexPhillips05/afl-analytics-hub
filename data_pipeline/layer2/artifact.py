from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import pandas as pd

from layer2.calibration import win_prob

ELO_PROB_COLUMN = "elo_home_win_prob"


@dataclass
class TrainedModel:
    """A fitted Layer 2 model plus everything needed to use it.

    The margin and the win probability are chosen separately: the probability comes either from the Elo engine
    (`prob_source="elo_engine"`, read from the features) or from a margin model's logistic curve (`"margin"`).
    """
    kind: str                     # margin model: "baseline", "ridge" or "xgboost"
    estimator: Any                # fitted sklearn-compatible margin estimator
    feature_names: list[str]      # margin model input columns, in order
    elo_config_name: str          # Elo config the features were built with (e.g. "TUNED_CONFIG")
    trained_seasons: tuple[int, int]
    params: dict
    prob_source: str = "elo_engine"            # "elo_engine" or "margin"
    prob_kind: str | None = None               # prob_source="margin": which model's curve
    prob_estimator: Any = None                 # prob_source="margin": fitted estimator for that curve
    prob_feature_names: list[str] | None = None
    scale: float | None = None                 # prob_source="margin": logistic scale s

    def predict(self, features: pd.DataFrame) -> pd.DataFrame:
        prob_columns = [ELO_PROB_COLUMN] if self.prob_source == "elo_engine" else self.prob_feature_names
        missing = [c for c in dict.fromkeys([*self.feature_names, *prob_columns]) if c not in features.columns]
        if missing:
            raise ValueError(f"Missing feature columns: {missing}")
        margin = self.estimator.predict(features[self.feature_names].astype(float))
        if self.prob_source == "elo_engine":
            prob = features[ELO_PROB_COLUMN].astype(float).to_numpy()
        else:
            prob = win_prob(self.prob_estimator.predict(features[self.prob_feature_names].astype(float)), self.scale)
        return pd.DataFrame({"pred_home_margin": margin, "pred_home_win_prob": prob}, index=features.index)


def save(model: TrainedModel, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, path)


def load(path: Path) -> TrainedModel:
    model = joblib.load(path)
    if not isinstance(model, TrainedModel):
        raise TypeError(f"{path} does not contain a TrainedModel")
    return model
