import math

import pytest

from elo.config import EloConfig
from elo.history import build_history
from features.build import build_features, elo_surprise, feature_columns
from tests.features.helpers import make_team_stats


def test_build_features_rows_targets_and_elo(season_matches):
    stats = make_team_stats(season_matches)

    f = build_features(season_matches, stats, EloConfig())

    assert list(f["match_id"]) == [m.match_id for m in season_matches]
    assert list(f["target_home_margin"]) == [25, 10, -14, 0]
    assert list(f["target_home_result"]) == [1.0, 1.0, 0.0, 0.5]
    elo = build_history(season_matches, EloConfig())
    assert list(f["elo_diff"]) == pytest.approx(list(elo["home_rating_pre"] - elo["away_rating_pre"]))
    assert list(f["elo_home_win_prob"]) == pytest.approx(list(elo["expected_home_win_prob"]))


def test_feature_columns_exclude_identifiers_and_targets(season_matches):
    cols = feature_columns(build_features(season_matches, make_team_stats(season_matches), EloConfig()))

    assert "elo_diff" in cols and "form_margin_diff" in cols and "rest_diff" in cols
    assert not any(c.startswith("target_") for c in cols)
    assert "match_id" not in cols and "date" not in cols


def test_form_and_rest_differences_have_home_minus_away_sign(season_matches):
    i50 = {("afltables-1", "Richmond"): 60.0, ("afltables-1", "Carlton"): 40.0}
    f = build_features(season_matches, make_team_stats(season_matches, i50=i50), EloConfig())

    # Match 3: Geelong (home; earlier: lost by 10 in match 2) v Richmond (away; earlier: won by 25 in match 1).
    assert f.loc[2, "form_margin_diff"] == pytest.approx(-10 - 25)
    assert f.loc[2, "form_inside_50s_net_diff"] == pytest.approx(0 - 20)
    assert f.loc[2, "home_days_rest"] == 14 and f.loc[2, "away_days_rest"] == 21
    assert f.loc[2, "rest_diff"] == 0                       # both capped at 9
    assert bool(f.loc[2, "away_off_bye"]) and bool(f.loc[2, "home_off_bye"])
    # Match 1: nobody has played yet; match 4: new season, form resets.
    for row in (0, 3):
        assert math.isnan(f.loc[row, "form_margin_diff"]) and math.isnan(f.loc[row, "rest_diff"])
    assert (f.loc[3, "home_games_this_season"], f.loc[3, "away_games_this_season"]) == (0, 0)


def test_elo_surprise_is_adjusted_margin_minus_elo_expected_margin(season_matches):
    config = EloConfig()
    elo = build_history(season_matches, config)

    surprise = elo_surprise(elo, config)

    p = elo["expected_home_win_prob"]
    expected_margin = config.outcome_scale * (p / (1 - p)).map(math.log)    # outcome_scale * logit(p)
    assert list(surprise) == pytest.approx(list(elo["adjusted_margin"] - expected_margin))


def test_form_vs_elo_diff_has_home_minus_away_sign_and_resets(season_matches):
    config = EloConfig()
    s = elo_surprise(build_history(season_matches, config), config)

    f = build_features(season_matches, make_team_stats(season_matches), config)

    assert "form_vs_elo_diff" in feature_columns(f)
    # Match 3: Geelong (home; earlier: away in match 2, so -s[1]) v Richmond (away; earlier: home in match 1, +s[0]).
    assert f.loc[2, "form_vs_elo_diff"] == pytest.approx(-s[1] - s[0])
    # Match 2: Geelong has no earlier game; match 4: new season.
    assert math.isnan(f.loc[1, "form_vs_elo_diff"]) and math.isnan(f.loc[3, "form_vs_elo_diff"])
