import pandas as pd

REST_CAP_DAYS = 9    # CLAUDE.md: cap each side's rest before differencing (limits outlier influence)
BYE_MIN_DAYS = 10    # CLAUDE.md: a break of more than 10 days counts as coming off a bye


def days_rest(team_games: pd.DataFrame) -> pd.Series:
    """Days since each team's previous game in the same season (NaN for its first game of the season).

    `team_games` has one row per team per match with columns team, season, date (datetime64), in
    chronological order. The off-season isn't rest, so it's never counted.
    """
    return team_games.groupby(["team", "season"], sort=False)["date"].diff().dt.days


def rest_features(home_days_rest: pd.Series, away_days_rest: pd.Series) -> pd.DataFrame:
    """Per-match rest features from each side's days rest (aligned Series, NaN = first game)."""
    return pd.DataFrame({
        "home_days_rest": home_days_rest,
        "away_days_rest": away_days_rest,
        "rest_diff": home_days_rest.clip(upper=REST_CAP_DAYS) - away_days_rest.clip(upper=REST_CAP_DAYS),
        "home_off_bye": home_days_rest > BYE_MIN_DAYS,   # NaN > 10 is False
        "away_off_bye": away_days_rest > BYE_MIN_DAYS,
    })
