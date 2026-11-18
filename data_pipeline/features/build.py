import pandas as pd

from elo.config import EloConfig
from elo.history import build_history
from elo.models import MatchResult
from features.form import FORM_VALUES, rolling_form, team_game_values
from features.rest import days_rest, rest_features

ID_COLUMNS = ["match_id", "season", "round_number", "date", "home_team", "away_team"]
TARGET_COLUMNS = ["target_home_margin", "target_home_result"]


def _team_games(matches: list[MatchResult], team_stats: pd.DataFrame) -> pd.DataFrame:
    """Two rows per match (home then away) with the team's and its opponent's totals, in match order."""
    stats = team_stats.set_index(["match_id", "team"])
    rows = []
    for order, m in enumerate(matches):
        sides = [(m.home_team, m.away_team, True, m.home_goals, m.home_behinds, m.home_score, m.away_score),
                 (m.away_team, m.home_team, False, m.away_goals, m.away_behinds, m.away_score, m.home_score)]
        for team, opp, is_home, goals, behinds, score, opp_score in sides:
            own, theirs = stats.loc[(m.match_id, team)], stats.loc[(m.match_id, opp)]
            rows.append({
                "order": order, "match_id": m.match_id, "season": m.season, "date": m.date, "team": team,
                "is_home": is_home, "goals": goals, "behinds": behinds, "score": score, "opp_score": opp_score,
                "inside_50s": own["inside_50s"], "opp_inside_50s": theirs["inside_50s"],
                "contested_possessions": own["contested_possessions"],
                "opp_contested_possessions": theirs["contested_possessions"],
                "clearances": own["clearances"], "opp_clearances": theirs["clearances"],
            })
    games = pd.DataFrame(rows)
    games["date"] = pd.to_datetime(games["date"])
    return games


def build_features(matches: list[MatchResult], team_stats: pd.DataFrame, elo_config: EloConfig) -> pd.DataFrame:
    """One row per match (chronological): identifiers, Layer 2 features, and target_* labels.

    `matches` must be in chronological order (as read_matches returns them); `team_stats` is
    read_team_stats output covering every match. Every feature uses only pre-kick-off information.
    """
    games = _team_games(matches, team_stats)
    games["days_rest"] = days_rest(games)
    form = rolling_form(games, team_game_values(games))
    home, away = games[games["is_home"]].reset_index(drop=True), games[~games["is_home"]].reset_index(drop=True)
    home_form, away_form = form[games["is_home"].to_numpy()].reset_index(drop=True), form[~games["is_home"].to_numpy()].reset_index(drop=True)

    elo = build_history(matches, elo_config)
    out = pd.DataFrame({
        "match_id": [m.match_id for m in matches],
        "season": [m.season for m in matches],
        "round_number": [m.round_number for m in matches],
        "date": home["date"],
        "home_team": home["team"],
        "away_team": away["team"],
        "is_final": [m.is_final for m in matches],
        "elo_diff": elo["home_rating_pre"] - elo["away_rating_pre"],
        "vai_diff": elo["home_vai"] - elo["away_vai"],
        "elo_home_win_prob": elo["expected_home_win_prob"],
    })
    out = pd.concat([out, rest_features(home["days_rest"], away["days_rest"])], axis=1)
    for value in FORM_VALUES:
        out[f"form_{value}_diff"] = home_form[value] - away_form[value]
    out["home_games_this_season"] = home_form["games_this_season"]
    out["away_games_this_season"] = away_form["games_this_season"]

    margin = home["score"] - away["score"]
    out["target_home_margin"] = margin
    out["target_home_result"] = (margin > 0).astype(float) + 0.5 * (margin == 0)
    return out


def feature_columns(features: pd.DataFrame) -> list[str]:
    """The model inputs: every column that isn't an identifier or a target."""
    return [c for c in features.columns if c not in ID_COLUMNS and not c.startswith("target_")]
