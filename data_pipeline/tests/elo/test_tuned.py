import pytest

from elo.config import EloConfig
from elo.tuned import TUNED_CONFIG
from elo.tuning import TUNABLE_GRIDS


def test_tuned_values_are_on_the_tuning_grids():
    for name, grid in TUNABLE_GRIDS.items():
        assert getattr(TUNED_CONFIG, name) in grid, name


def test_tuned_score_weights_are_a_true_split():
    assert TUNED_CONFIG.scoring_shot_weight + TUNED_CONFIG.actual_score_weight == pytest.approx(1.0)


def test_untuned_bookkeeping_settings_keep_tier0_defaults():
    defaults = EloConfig()
    for name in ["initial_rating", "league_avg_conversion", "fallback_conversion"]:
        assert getattr(TUNED_CONFIG, name) == getattr(defaults, name)
