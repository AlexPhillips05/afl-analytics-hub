from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import pandas as pd

from layer2.calibration import win_prob


@dataclass
class TrainedModel:
    """A fitted Layer 2 model plus everything needed to use it."""
    kind: str                     # "baseline", "ridge" or "xgboost"
    estimator: Any                # fitted sklearn-compatible estimator
    feature_names: list[str]      # input columns, in order
    scale: float                  # logistic scale s for win probability
    elo_config_name: str          # Elo config the features were built with (e.g. "TUNED_CONFIG")
    trained_seasons: tuple[int, int]
    params: dict

    def predict(self, features: pd.DataFrame) -> pd.DataFrame:
        missing = [c for c in self.feature_names if c not in features.columns]
        if missing:
            raise ValueError(f"Missing feature columns: {missing}")
        margin = self.estimator.predict(features[self.feature_names].astype(float))
        return pd.DataFrame({"pred_home_margin": margin, "pred_home_win_prob": win_prob(margin, self.scale)},
                            index=features.index)


def save(model: TrainedModel, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, path)


def load(path: Path) -> TrainedModel:
    model = joblib.load(path)
    if not isinstance(model, TrainedModel):
        raise TypeError(f"{path} does not contain a TrainedModel")
    return model
