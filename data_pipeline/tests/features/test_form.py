import math

import pandas as pd
import pytest

from features.form import rolling_form, team_game_values

W = 0.5 ** (1 / 5)   # weight of a game one step older, for a 5-game half-life


def _values(team_seasons, margins):
    games = pd.DataFrame(team_seasons, columns=["team", "season"])
    return games, pd.DataFrame({"margin": margins})


def test_rolling_form_is_shifted_weighted_average_of_earlier_games():
    games, values = _values([("A", 2024)] * 4, [10.0, 20.0, -6.0, 99.0])

    form = rolling_form(games, values)

    assert math.isnan(form["margin"][0])                                  # no earlier game
    assert form["margin"][1] == pytest.approx(10.0)                       # just game 1
    assert form["margin"][2] == pytest.approx((W * 10 + 20) / (W + 1))    # games 1-2, recent weighted more
    assert form["margin"][3] == pytest.approx((W * W * 10 + W * 20 - 6) / (W * W + W + 1))
    assert list(form["games_this_season"]) == [0, 1, 2, 3]


def test_rolling_form_resets_each_season_and_is_per_team():
    games, values = _values([("A", 2024), ("B", 2024), ("A", 2024), ("A", 2025), ("A", 2025)],
                            [10.0, 50.0, 20.0, 30.0, 40.0])

    form = rolling_form(games, values)

    assert form["margin"][2] == pytest.approx(10.0)       # A's own earlier game, not B's
    assert math.isnan(form["margin"][3])                  # 2025 starts fresh
    assert form["margin"][4] == pytest.approx(30.0)
    assert list(form["games_this_season"]) == [0, 0, 1, 0, 1]


def test_changing_a_games_own_result_cannot_change_its_form():
    games, values = _values([("A", 2024)] * 3, [10.0, 20.0, 30.0])
    before = rolling_form(games, values)
    values.loc[1, "margin"] = -100.0

    after = rolling_form(games, values)

    assert after["margin"][1] == before["margin"][1]      # game 1's form ignores game 1's result
    assert after["margin"][2] != before["margin"][2]      # but the next game sees it


def test_team_game_values():
    g = pd.DataFrame([{"score": 80, "opp_score": 70, "goals": 12, "behinds": 8, "inside_50s": 50,
                       "opp_inside_50s": 45, "contested_possessions": 130, "opp_contested_possessions": 140,
                       "clearances": 40, "opp_clearances": 30},
                      {"score": 60, "opp_score": 60, "goals": 0, "behinds": 0, "inside_50s": 0,
                       "opp_inside_50s": 10, "contested_possessions": 100, "opp_contested_possessions": 100,
                       "clearances": 30, "opp_clearances": 30}])

    v = team_game_values(g)

    assert list(v.loc[0, ["margin", "win", "inside_50s_net", "contested_poss_net", "clearances_net"]]) == [10, 1.0, 5, -10, 10]
    assert v.loc[0, "i50_efficiency"] == pytest.approx(20 / 50)
    assert v.loc[0, "kicking_efficiency"] == pytest.approx(12 / 20)
    assert v.loc[1, "win"] == 0.5
    assert math.isnan(v.loc[1, "i50_efficiency"]) and math.isnan(v.loc[1, "kicking_efficiency"])
