import math

import pandas as pd
from psycopg2.extras import execute_values

from elo.models import MatchResult
from elo.venues import TEAM_STATE

# AFL Tables player pages use different names from its match results for three clubs.
TEAM_NAME_ALIASES: dict[str, str] = {
    "Greater Western Sydney": "GWS",
    "Western Bulldogs": "Footscray",
    "Kangaroos": "North Melbourne",
}

# Summed per team per match (same names in raw_afltables_player_stats and team_match_stats).
STAT_COLUMNS = (
    "kicks", "handballs", "marks", "tackles", "inside_50s", "rebounds", "clearances",
    "contested_possessions", "uncontested_possessions", "clangers", "frees_for", "frees_against",
    "hit_outs", "contested_marks", "marks_inside_50", "one_percenters", "goal_assists", "bounces",
)

RAW_KEY_COLUMNS = ("date", "home_team", "away_team", "playing_for")


def canonical_team(name: str) -> str:
    """Player-stats team name -> the name used in matches/teams. Unknown names raise."""
    canonical = TEAM_NAME_ALIASES.get(name, name)
    if canonical not in TEAM_STATE:
        raise ValueError(f"Unknown team {name!r}: add it to TEAM_NAME_ALIASES or elo/venues.py")
    return canonical


def read_raw_player_stats(conn) -> pd.DataFrame:
    columns = (*RAW_KEY_COLUMNS, *STAT_COLUMNS)
    with conn.cursor() as cur:
        cur.execute(f"SELECT {', '.join(columns)} FROM raw_afltables_player_stats")
        rows = cur.fetchall()
    return pd.DataFrame(rows, columns=list(columns))


def aggregate_team_stats(players: pd.DataFrame, matches: list[MatchResult]) -> pd.DataFrame:
    """Sum player rows into one row per team per match. Pure.

    Joins player rows to matches on (date, home team, away team) after name mapping. A stat is NaN
    when every player value is null. Raises ValueError unless every match gets exactly two team rows
    (its home and away teams) and every player row belongs to a known match.
    """
    p = players.copy()
    for col in ("home_team", "away_team", "playing_for"):
        p[col] = p[col].map(canonical_team)
    match_ids = {(m.date, m.home_team, m.away_team): m.match_id for m in matches}
    p["match_id"] = [match_ids.get(key) for key in zip(p["date"], p["home_team"], p["away_team"])]

    unmatched = p.loc[p["match_id"].isna(), ["date", "home_team", "away_team"]].drop_duplicates()
    if not unmatched.empty:
        raise ValueError(f"Player rows for {len(unmatched)} unknown matches, e.g. {unmatched.head(3).to_dict('records')}")

    grouped = p.groupby(["match_id", "playing_for"], sort=False)
    stats = grouped[list(STAT_COLUMNS)].sum(min_count=1)
    stats.insert(0, "players", grouped.size())
    stats = stats.reset_index().rename(columns={"playing_for": "team"})

    sides = {m.match_id: (m.home_team, m.away_team) for m in matches}
    stats["is_home"] = [sides[mid][0] == team for mid, team in zip(stats["match_id"], stats["team"])]
    wrong_team = [mid for mid, team in zip(stats["match_id"], stats["team"]) if team not in sides[mid]]
    counts = stats.groupby("match_id").size()
    bad = sorted(set(wrong_team) | set(counts[counts != 2].index) | (set(sides) - set(counts.index)))
    if bad:
        raise ValueError(f"{len(bad)} matches don't have exactly their two teams' stats, e.g. {bad[:5]}")

    # Chronological match order (as in `matches`), home team first.
    stats["_order"] = stats["match_id"].map({m.match_id: i for i, m in enumerate(matches)})
    stats = stats.sort_values(["_order", "is_home"], ascending=[True, False])
    return stats[["match_id", "team", "is_home", "players", *STAT_COLUMNS]].reset_index(drop=True)


def _db_value(value):
    return None if value is None or (isinstance(value, float) and math.isnan(value)) else int(value)


def replace_team_stats(conn, team_stats: pd.DataFrame, team_ids: dict[str, int]) -> int:
    """Replace every row of team_match_stats in one transaction."""
    rows = [
        (row.match_id, team_ids[row.team], bool(row.is_home), int(row.players),
         *(_db_value(getattr(row, c)) for c in STAT_COLUMNS))
        for row in team_stats.itertuples(index=False)
    ]
    with conn, conn.cursor() as cur:
        cur.execute("DELETE FROM team_match_stats")
        execute_values(
            cur,
            f"INSERT INTO team_match_stats (match_id, team_id, is_home, players, {', '.join(STAT_COLUMNS)}) VALUES %s",
            rows,
        )
    return len(rows)


def read_team_stats(conn) -> pd.DataFrame:
    """All team_match_stats rows with team names, in chronological match order (home before away)."""
    with conn.cursor() as cur:
        cur.execute(f"""
            SELECT s.match_id, t.name, s.is_home, s.players, {', '.join('s.' + c for c in STAT_COLUMNS)}
            FROM team_match_stats s
            JOIN teams t ON t.id = s.team_id
            JOIN matches m ON m.id = s.match_id
            ORDER BY m.date, m.afltables_game, s.is_home DESC
        """)
        rows = cur.fetchall()
    frame = pd.DataFrame(rows, columns=["match_id", "team", "is_home", "players", *STAT_COLUMNS])
    return frame.astype({c: "float64" for c in STAT_COLUMNS})
