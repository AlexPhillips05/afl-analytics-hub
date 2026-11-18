import math

import pandas as pd

from features.rest import days_rest, rest_features


def _games(rows):
    return pd.DataFrame(rows, columns=["team", "season", "date"]).assign(date=lambda d: pd.to_datetime(d["date"]))


def test_days_rest_within_season_and_nan_for_first_game():
    games = _games([
        ("A", 2024, "2024-03-14"), ("B", 2024, "2024-03-14"),
        ("A", 2024, "2024-03-20"),                                # 6 days
        ("A", 2024, "2024-04-03"),                                # 14 days
        ("A", 2025, "2025-03-13"),                                # new season: not 344 days of rest
    ])

    rest = days_rest(games)

    assert math.isnan(rest[0]) and math.isnan(rest[1]) and math.isnan(rest[4])
    assert list(rest[2:4]) == [6, 14]


def test_rest_features_cap_and_bye_flags():
    home = pd.Series([6.0, 14.0, float("nan"), 11.0])
    away = pd.Series([8.0, 6.0, 7.0, 10.0])

    f = rest_features(home, away)

    assert list(f["rest_diff"][:2]) == [-2.0, 3.0]        # 14 capped to 9
    assert math.isnan(f["rest_diff"][2])
    assert f["rest_diff"][3] == 0.0                       # 11 and 10 both capped to 9
    assert list(f["home_off_bye"]) == [False, True, False, True]
    assert list(f["away_off_bye"]) == [False, False, False, False]   # exactly 10 days is not a bye
