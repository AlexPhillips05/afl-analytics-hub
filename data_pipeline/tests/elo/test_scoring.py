import pytest

from elo.scoring import adjusted_score, conversion_rate, expected_points_per_shot


def test_conversion_rate_is_goals_over_scoring_shots():
    # e.g. two matches: 10.5 v 8.6 and 12.4 v 9.7 -> 39 goals from 61 scoring shots
    assert conversion_rate(goals=39, scoring_shots=61, fallback=0.50) == pytest.approx(0.639344262295082)


def test_conversion_rate_falls_back_when_no_shots():
    assert conversion_rate(goals=0, scoring_shots=0, fallback=0.50) == 0.50


def test_expected_points_per_shot():
    assert expected_points_per_shot(0.5) == pytest.approx(3.5)


def test_adjusted_score_blends_shot_value_and_actual_score():
    result = adjusted_score(
        scoring_shots=15,
        actual_score=65,
        league_avg_conversion=0.5,
        scoring_shot_weight=0.65,
        actual_score_weight=0.35,
    )

    assert result == pytest.approx(56.875)
