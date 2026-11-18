import math

import pandas as pd
import pytest

from elo.config import EloConfig
from elo.tuning import TUNABLE_GRIDS, coordinate_search, mean_bits, scored_mask, summary, with_value


def _history(rows):
    return pd.DataFrame(rows, columns=["season", "home_team", "away_team",
                                       "expected_home_win_prob", "home_score", "away_score"])


def test_scored_mask_applies_range_and_anomaly_exclusions():
    h = _history([
        (2009, "A", "B", 0.5, 1, 0),          # before range
        (2016, "Essendon", "B", 0.5, 1, 0),   # Essendon home 2016
        (2016, "B", "Essendon", 0.5, 1, 0),   # Essendon away 2016
        (2016, "A", "B", 0.5, 1, 0),          # other 2016 game: kept
        (2017, "Essendon", "B", 0.5, 1, 0),   # Essendon other season: kept
        (2020, "A", "B", 0.5, 1, 0),          # COVID
        (2021, "A", "B", 0.5, 1, 0),          # last season in range: kept
        (2022, "A", "B", 0.5, 1, 0),          # after range
    ])

    assert list(scored_mask(h, 2010, 2021)) == [False, False, False, True, True, False, True, False]


def test_mean_bits_over_scored_games_only():
    h = _history([
        (2015, "A", "B", 0.75, 100, 60),   # home win: 1 + log2(0.75)
        (2015, "A", "B", 0.75, 60, 100),   # away win: 1 + log2(0.25) = -1
        (2020, "A", "B", 0.99, 60, 100),   # COVID: ignored
    ])

    assert mean_bits(h, 2010, 2021) == pytest.approx(((1 + math.log2(0.75)) + -1.0) / 2)


def test_summary_over_scored_games():
    h = _history([
        (2023, "A", "B", 0.75, 100, 60),   # tipped home, home won
        (2023, "A", "B", 0.75, 60, 100),   # tipped home, away won
        (2024, "A", "B", 0.40, 80, 80),    # draw: correct tip, home result 0.5
        (2020, "A", "B", 0.50, 1, 0),      # COVID: ignored
    ])

    s = summary(h, 2022, 2026)

    assert s["games"] == 3
    assert s["tip_accuracy"] == pytest.approx(2 / 3)
    assert s["bits_per_game"] == pytest.approx(
        ((1 + math.log2(0.75)) + -1.0 + (1 + 0.5 * math.log2(0.40 * 0.60))) / 3)
    assert s["home_bias"] == pytest.approx(((1 - 0.75) + (0 - 0.75) + (0.5 - 0.40)) / 3)


def test_with_value_sets_one_setting():
    config = with_value(EloConfig(), "k_early", 40.0)

    assert config.k_early == 40.0
    assert config.k_late == EloConfig().k_late


def test_with_value_keeps_score_weights_tied():
    config = with_value(EloConfig(), "scoring_shot_weight", 0.55)

    assert config.scoring_shot_weight == 0.55
    assert config.actual_score_weight == pytest.approx(0.45)


def test_with_value_rejects_untunable_names():
    with pytest.raises(ValueError, match="initial_rating"):
        with_value(EloConfig(), "initial_rating", 1400.0)


def test_every_grid_contains_the_tier0_default():
    defaults = EloConfig()
    for name, grid in TUNABLE_GRIDS.items():
        assert getattr(defaults, name) in grid, name


GRIDS = {"k_early": (20.0, 30.0, 38.0, 40.0, 50.0), "k_late": (10.0, 16.0, 22.0, 28.0)}


def _peaked(config):
    # Separable objective, best at k_early=40, k_late=16 (both interior grid points).
    return -((config.k_early - 40.0) ** 2) - ((config.k_late - 16.0) ** 2)


def test_coordinate_search_finds_the_optimum_and_converges():
    result = coordinate_search(_peaked, EloConfig(), GRIDS)

    assert result.best_config.k_early == 40.0
    assert result.best_config.k_late == 16.0
    assert result.best_score == 0.0
    assert result.start_score == -(2.0 ** 2) - (6.0 ** 2)
    assert result.converged is True
    assert result.passes == 2   # pass 1 moves both, pass 2 confirms nothing changes
    assert result.at_grid_edge == ()


def test_coordinate_search_reports_final_pass_sensitivity():
    result = coordinate_search(_peaked, EloConfig(), GRIDS)

    # Final pass: k_late fixed at 16, so k_early's grid spans -(20^2) .. 0.
    assert result.sensitivity["k_early"] == (-400.0, 0.0)
    assert result.sensitivity["k_late"] == (-144.0, 0.0)


def test_coordinate_search_ignores_improvements_below_threshold():
    tiny = lambda config: 1e-6 * config.k_early   # noqa: E731 — best is k_early=50, but gain is tiny

    result = coordinate_search(tiny, EloConfig(), {"k_early": GRIDS["k_early"]}, min_improvement=1e-4)

    assert result.best_config.k_early == 38.0
    assert result.converged is True


def test_coordinate_search_flags_optimum_at_grid_edge():
    rising = lambda config: config.k_early   # noqa: E731 — keeps improving to the top of the grid

    result = coordinate_search(rising, EloConfig(), {"k_early": GRIDS["k_early"]})

    assert result.best_config.k_early == 50.0
    assert result.at_grid_edge == ("k_early",)


def test_coordinate_search_stops_at_max_passes_without_converging():
    # Pass 1 still adopts changes, so with max_passes=1 the search stops unconverged.
    result = coordinate_search(_peaked, EloConfig(), GRIDS, max_passes=1)

    assert result.passes == 1
    assert result.converged is False
    assert result.best_config.k_early == 40.0
