"""Synthetic matches and team stats for feature tests."""
import pandas as pd

from db.team_stats import STAT_COLUMNS
from elo.models import MatchResult


def make_match(game, match_date, home, away, hg=12, hb=8, ag=10, ab=6, season=None):
    return MatchResult(season=season or match_date.year, round_number=1, is_final=False, home_team=home,
                       away_team=away, home_goals=hg, home_behinds=hb, away_goals=ag, away_behinds=ab,
                       match_id=f"afltables-{game}", date=match_date, venue="M.C.G.", round_code="R1")


def make_team_stats(matches, i50=None, cp=None, cl=None):
    """team_match_stats-shaped frame; i50/cp/cl map (match_id, team) -> value (default 50/130/35)."""
    rows = []
    for m in matches:
        for team, is_home in ((m.home_team, True), (m.away_team, False)):
            row = {"match_id": m.match_id, "team": team, "is_home": is_home, "players": 22}
            row.update({c: 1.0 for c in STAT_COLUMNS})
            row["inside_50s"] = (i50 or {}).get((m.match_id, team), 50.0)
            row["contested_possessions"] = (cp or {}).get((m.match_id, team), 130.0)
            row["clearances"] = (cl or {}).get((m.match_id, team), 35.0)
            rows.append(row)
    return pd.DataFrame(rows)
