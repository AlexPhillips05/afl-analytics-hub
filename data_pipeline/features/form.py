import numpy as np
import pandas as pd

HALF_LIFE_GAMES = 5  # CLAUDE.md: exponentially weighted, 5-game half-life

# Per team-game values that become rolling form (team perspective).
FORM_VALUES = (
    "margin", "win", "inside_50s_net", "contested_poss_net", "clearances_net",
    "i50_efficiency", "kicking_efficiency", "vs_elo",
)


def team_game_values(team_games: pd.DataFrame) -> pd.DataFrame:
    """Each team's values for one game, from its own and its opponent's totals.

    Needs columns: score, opp_score, goals, behinds, inside_50s, opp_inside_50s,
    contested_possessions, opp_contested_possessions, clearances, opp_clearances, vs_elo (adjusted margin minus
    Elo's expected margin, from features.build.elo_surprise).
    """
    g = team_games
    margin = g["score"] - g["opp_score"]
    shots = g["goals"] + g["behinds"]
    return pd.DataFrame({
        "margin": margin,
        "win": np.select([margin > 0, margin == 0], [1.0, 0.5], 0.0),
        "inside_50s_net": g["inside_50s"] - g["opp_inside_50s"],
        "contested_poss_net": g["contested_possessions"] - g["opp_contested_possessions"],
        "clearances_net": g["clearances"] - g["opp_clearances"],
        "i50_efficiency": shots / g["inside_50s"].replace(0, np.nan),
        "kicking_efficiency": g["goals"] / shots.replace(0, np.nan),
        "vs_elo": g["vs_elo"],
    }, index=g.index)


def rolling_form(team_games: pd.DataFrame, values: pd.DataFrame, half_life: float = HALF_LIFE_GAMES) -> pd.DataFrame:
    """Season-reset rolling form BEFORE each game, plus the count of earlier games this season.

    `team_games` (columns team, season) and `values` share an index and are in chronological order.
    For each (team, season) the weighted average is taken over the team's games and then shifted by one,
    so a game's form only uses earlier games: no leakage, and NaN for a team's first game of a season.
    """
    groups = values.groupby([team_games["team"], team_games["season"]], sort=False)
    form = groups.transform(lambda s: s.ewm(halflife=half_life).mean().shift(1))
    form["games_this_season"] = groups.cumcount()
    return form
