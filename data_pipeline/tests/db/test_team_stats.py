import math
from datetime import date

import pandas as pd
import pytest

from db.matches import replace_matches
from db.reference import sync_reference_data
from db.team_stats import (STAT_COLUMNS, aggregate_team_stats, canonical_team, read_raw_player_stats,
                           read_team_stats, replace_team_stats)
from elo.models import MatchResult


def _match(game, match_date, home, away, venue="M.C.G."):
    return MatchResult(season=match_date.year, round_number=1, is_final=False, home_team=home, away_team=away,
                       home_goals=10, home_behinds=10, away_goals=8, away_behinds=8,
                       match_id=f"afltables-{game}", date=match_date, venue=venue, round_code="R1")


def _player(match_date, home, away, playing_for, **stats):
    row = {"date": match_date, "home_team": home, "away_team": away, "playing_for": playing_for}
    row.update({c: stats.get(c, 1) for c in STAT_COLUMNS})
    return row


D1, D2 = date(2024, 3, 14), date(2024, 3, 21)
MATCHES = [_match(1, D1, "GWS", "Footscray"), _match(2, D2, "North Melbourne", "Sydney", venue="Docklands")]


def _players():
    # Player-page names: "Greater Western Sydney", "Western Bulldogs", "Kangaroos".
    rows = []
    for i in range(3):
        rows.append(_player(D1, "Greater Western Sydney", "Western Bulldogs", "Greater Western Sydney", inside_50s=i + 1))
        rows.append(_player(D1, "Greater Western Sydney", "Western Bulldogs", "Western Bulldogs", inside_50s=2, goal_assists=None))
        rows.append(_player(D2, "Kangaroos", "Sydney", "Kangaroos"))
        rows.append(_player(D2, "Kangaroos", "Sydney", "Sydney", tackles=4))
    return pd.DataFrame(rows)


def test_canonical_team_maps_aliases_and_rejects_unknown_names():
    assert canonical_team("Greater Western Sydney") == "GWS"
    assert canonical_team("Western Bulldogs") == "Footscray"
    assert canonical_team("Kangaroos") == "North Melbourne"
    assert canonical_team("Sydney") == "Sydney"
    with pytest.raises(ValueError, match="Tasmania"):
        canonical_team("Tasmania")


def test_aggregate_sums_players_per_team_in_match_order_home_first():
    stats = aggregate_team_stats(_players(), MATCHES)

    assert list(zip(stats["match_id"], stats["team"], stats["is_home"])) == [
        ("afltables-1", "GWS", True), ("afltables-1", "Footscray", False),
        ("afltables-2", "North Melbourne", True), ("afltables-2", "Sydney", False),
    ]
    assert list(stats["players"]) == [3, 3, 3, 3]
    assert list(stats["inside_50s"]) == [6, 6, 3, 3]       # 1+2+3 for GWS; 2*3 for Footscray
    assert list(stats["tackles"]) == [3, 3, 3, 12]


def test_aggregate_gives_nan_when_every_player_value_is_null():
    stats = aggregate_team_stats(_players(), MATCHES)

    assert math.isnan(stats.loc[1, "goal_assists"])   # Footscray: all None
    assert stats.loc[0, "goal_assists"] == 3


def test_aggregate_rejects_a_match_with_only_one_team():
    players = _players()
    players = players[players["playing_for"] != "Sydney"]

    with pytest.raises(ValueError, match="afltables-2"):
        aggregate_team_stats(players, MATCHES)


def test_aggregate_rejects_a_match_with_no_player_rows():
    extra = MATCHES + [_match(3, date(2024, 3, 28), "Geelong", "Carlton")]

    with pytest.raises(ValueError, match="afltables-3"):
        aggregate_team_stats(_players(), extra)


def test_aggregate_rejects_player_rows_for_an_unknown_match():
    players = pd.concat([_players(), pd.DataFrame([_player(date(2024, 4, 1), "Geelong", "Carlton", "Geelong")])])

    with pytest.raises(ValueError, match="unknown matches"):
        aggregate_team_stats(players, MATCHES)


def test_replace_and_read_team_stats_round_trip(db_conn):
    team_ids, venue_ids = sync_reference_data(db_conn)
    replace_matches(db_conn, MATCHES, team_ids, venue_ids)
    stats = aggregate_team_stats(_players(), MATCHES)

    assert replace_team_stats(db_conn, stats, team_ids) == 4
    assert replace_team_stats(db_conn, stats, team_ids) == 4   # replaces, doesn't duplicate

    read = read_team_stats(db_conn)
    pd.testing.assert_frame_equal(read, stats.astype({c: "float64" for c in STAT_COLUMNS}), check_dtype=False)


def test_read_raw_player_stats_returns_key_and_stat_columns(db_conn):
    with db_conn, db_conn.cursor() as cur:
        cur.execute("""INSERT INTO raw_afltables_player_stats (season, round, date, venue, home_team, away_team,
                       playing_for, first_name, surname, inside_50s, goal_assists)
                       VALUES (2024, '1', '2024-03-14', 'M.C.G.', 'Kangaroos', 'Sydney', 'Kangaroos', 'A', 'B', 4, NULL)""")

    raw = read_raw_player_stats(db_conn)

    assert list(raw.columns[:4]) == ["date", "home_team", "away_team", "playing_for"]
    assert set(STAT_COLUMNS) <= set(raw.columns)
    assert raw.loc[0, "inside_50s"] == 4 and raw.loc[0, "goal_assists"] is None
