import math

import pandas as pd
import pytest

from elo.evaluation import end_of_season_ratings, match_bits, season_metrics, tip_correct


def test_bits_home_win():
    assert match_bits(0.75, 100, 60) == pytest.approx(1 + math.log2(0.75))  # ≈ 0.585


def test_bits_away_win_against_confident_home_tip_is_negative():
    assert match_bits(0.75, 60, 100) == pytest.approx(1 + math.log2(0.25))  # = -1.0


def test_bits_draw():
    assert match_bits(0.75, 80, 80) == pytest.approx(1 + 0.5 * math.log2(0.75 * 0.25))  # ≈ -0.208


def test_bits_coin_flip_scores_zero():
    assert match_bits(0.5, 100, 60) == pytest.approx(0.0)


def test_tip_correct():
    assert tip_correct(0.6, 100, 60) is True    # tipped home, home won
    assert tip_correct(0.6, 60, 100) is False   # tipped home, away won
    assert tip_correct(0.4, 60, 100) is True    # tipped away, away won
    assert tip_correct(0.5, 100, 60) is True    # 0.5 tips home
    assert tip_correct(0.9, 80, 80) is True     # draws count as correct


def _history():
    # Minimal EloEngine-style output (+ scores). Two seasons, chronological.
    return pd.DataFrame([
        # season 2009: A beats B, then B beats A
        dict(match_id="m1", season=2009, home_team="A", away_team="B",
             home_rating_post=1510.0, away_rating_post=1490.0,
             expected_home_win_prob=0.5, rating_change=10.0, home_score=90, away_score=70),
        dict(match_id="m2", season=2009, home_team="B", away_team="A",
             home_rating_post=1500.0, away_rating_post=1500.0,
             expected_home_win_prob=0.4, rating_change=10.0, home_score=95, away_score=60),
        # season 2020: A beats C (away win), C v B draw
        dict(match_id="m3", season=2020, home_team="C", away_team="A",
             home_rating_post=1480.0, away_rating_post=1520.0,
             expected_home_win_prob=0.5, rating_change=-20.0, home_score=50, away_score=80),
        dict(match_id="m4", season=2020, home_team="C", away_team="B",
             home_rating_post=1484.0, away_rating_post=1496.0,
             expected_home_win_prob=0.45, rating_change=4.0, home_score=70, away_score=70),
    ])


def test_end_of_season_ratings_uses_each_teams_last_game():
    end = end_of_season_ratings(_history()).set_index(["season", "team"])["rating"]

    assert end[(2009, "A")] == 1500.0
    assert end[(2009, "B")] == 1500.0
    assert end[(2020, "A")] == 1520.0
    assert end[(2020, "B")] == 1496.0
    assert end[(2020, "C")] == 1484.0


def test_season_metrics():
    m = season_metrics(_history()).set_index("season")

    assert list(m.index) == [2009, 2020]
    assert m.loc[2009, "games"] == 2
    # m1: p=0.5 tips home, home won -> correct. m2: p=0.4 tips away, home won -> wrong.
    assert m.loc[2009, "tip_accuracy"] == pytest.approx(0.5)
    assert m.loc[2009, "home_baseline_accuracy"] == pytest.approx(1.0)
    assert m.loc[2009, "bits_total"] == pytest.approx(0.0 + (1 + math.log2(0.4)))
    assert m.loc[2009, "mean_abs_rating_change"] == pytest.approx(10.0)
    assert m.loc[2009, "end_rating_sd"] == pytest.approx(0.0)
    assert m.loc[2009, "end_rating_range"] == pytest.approx(0.0)
    assert m.loc[2009, "note"] == "warm-up"

    # m3: p=0.5 tips home, away won -> wrong. m4: draw -> correct.
    assert m.loc[2020, "tip_accuracy"] == pytest.approx(0.5)
    # baseline: m3 home lost -> wrong; m4 draw -> correct
    assert m.loc[2020, "home_baseline_accuracy"] == pytest.approx(0.5)
    assert m.loc[2020, "mean_abs_rating_change"] == pytest.approx(12.0)
    assert m.loc[2020, "end_rating_range"] == pytest.approx(1520.0 - 1484.0)
    assert m.loc[2020, "note"] == "COVID"
