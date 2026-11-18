import pandas as pd
from psycopg2.extras import execute_values

from elo.models import MatchResult

# raw_afltables_results column -> fitzRoy/AFL Tables column name. read_raw_results returns the
# AFL Tables names so elo.adapters.afltables_to_matches works unchanged.
RAW_COLUMNS: dict[str, str] = {
    "game": "Game",
    "date": "Date",
    "season": "Season",
    "round": "Round",
    "round_type": "Round.Type",
    "round_number": "Round.Number",
    "home_team": "Home.Team",
    "home_goals": "Home.Goals",
    "home_behinds": "Home.Behinds",
    "home_points": "Home.Points",
    "away_team": "Away.Team",
    "away_goals": "Away.Goals",
    "away_behinds": "Away.Behinds",
    "away_points": "Away.Points",
    "venue": "Venue",
    "margin": "Margin",
}

MATCH_COLUMNS = (
    "id", "afltables_game", "season", "round_number", "round_code", "is_final", "date",
    "venue_id", "home_team_id", "away_team_id", "home_goals", "home_behinds", "away_goals", "away_behinds",
)


def read_raw_results(conn) -> pd.DataFrame:
    with conn.cursor() as cur:
        cur.execute(f"SELECT {', '.join(RAW_COLUMNS)} FROM raw_afltables_results ORDER BY game")
        rows = cur.fetchall()
    return pd.DataFrame(rows, columns=list(RAW_COLUMNS.values()))


def _lookup(ids: dict[str, int], kind: str, name: str) -> int:
    try:
        return ids[name]
    except KeyError:
        raise KeyError(f"Unknown {kind} {name!r}: add it to elo/venues.py and re-run load_matches.py") from None


def match_rows(matches: list[MatchResult], team_ids: dict[str, int], venue_ids: dict[str, int]) -> list[tuple]:
    """One tuple per match, in MATCH_COLUMNS order. Pure."""
    return [
        (
            m.match_id,
            int(m.match_id.removeprefix("afltables-")),
            m.season,
            m.round_number,
            m.round_code,
            m.is_final,
            m.date,
            _lookup(venue_ids, "venue", m.venue),
            _lookup(team_ids, "team", m.home_team),
            _lookup(team_ids, "team", m.away_team),
            m.home_goals,
            m.home_behinds,
            m.away_goals,
            m.away_behinds,
        )
        for m in matches
    ]


def replace_matches(conn, matches: list[MatchResult], team_ids: dict[str, int], venue_ids: dict[str, int]) -> int:
    """Replace every row of `matches` in one transaction. Cascades to elo_ratings (recompute Elo afterwards)."""
    rows = match_rows(matches, team_ids, venue_ids)
    with conn, conn.cursor() as cur:
        cur.execute("DELETE FROM matches")
        execute_values(cur, f"INSERT INTO matches ({', '.join(MATCH_COLUMNS)}) VALUES %s", rows)
    return len(rows)


def read_matches(conn) -> list[MatchResult]:
    """All matches in chronological order (date, then AFL Tables game number), ready for EloEngine."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT m.id, m.season, m.round_number, m.is_final, ht.name, at.name,
                   m.home_goals, m.home_behinds, m.away_goals, m.away_behinds, m.date, v.name, m.round_code
            FROM matches m
            JOIN teams ht ON ht.id = m.home_team_id
            JOIN teams at ON at.id = m.away_team_id
            JOIN venues v ON v.id = m.venue_id
            ORDER BY m.date, m.afltables_game
        """)
        rows = cur.fetchall()
    return [
        MatchResult(
            season=season, round_number=round_number, is_final=is_final,
            home_team=home, away_team=away,
            home_goals=hg, home_behinds=hb, away_goals=ag, away_behinds=ab,
            match_id=match_id, date=date, venue=venue, round_code=round_code,
        )
        for match_id, season, round_number, is_final, home, away, hg, hb, ag, ab, date, venue, round_code in rows
    ]
