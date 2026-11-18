from datetime import date

import pandas as pd
import pytest

from db.elo_store import save_elo_run
from db.matches import read_matches, read_raw_results, replace_matches
from db.reference import sync_reference_data
from elo.adapters import afltables_to_matches
from elo.config import EloConfig
from elo.history import build_history
from elo.models import MatchResult


def _match(game, match_date, home="Sydney", away="GWS", venue="S.C.G.", **overrides):
    fields = dict(season=match_date.year, round_number=1, is_final=False, home_team=home, away_team=away,
                  home_goals=12, home_behinds=8, away_goals=10, away_behinds=11,
                  match_id=f"afltables-{game}", date=match_date, venue=venue, round_code="R2")
    return MatchResult(**{**fields, **overrides})


def _count(conn, table):
    with conn.cursor() as cur:
        cur.execute(f"SELECT count(*) FROM {table}")
        return cur.fetchone()[0]


def test_sync_reference_data_is_idempotent(db_conn):
    first = sync_reference_data(db_conn)
    second = sync_reference_data(db_conn)

    assert first == second
    assert len(first[0]) == 18 and len(first[1]) == 29
    assert _count(db_conn, "teams") == 18 and _count(db_conn, "venues") == 29


def test_replace_then_read_matches_round_trips_in_chronological_order(db_conn):
    team_ids, venue_ids = sync_reference_data(db_conn)
    matches = [
        _match(30, date(2025, 3, 20), home="West Coast", away="Fremantle", venue="Perth Stadium", is_final=True,
               round_number=25, round_code="WF"),
        _match(21, date(2025, 3, 13)),                                     # same day, higher game number
        _match(20, date(2025, 3, 13), home="Geelong", away="Hawthorn", venue="Kardinia Park"),
    ]

    assert replace_matches(db_conn, matches, team_ids, venue_ids) == 3

    assert read_matches(db_conn) == [matches[2], matches[1], matches[0]]


def test_replace_matches_leaves_only_the_new_set(db_conn):
    team_ids, venue_ids = sync_reference_data(db_conn)
    replace_matches(db_conn, [_match(1, date(2024, 3, 7)), _match(2, date(2024, 3, 8))], team_ids, venue_ids)

    replace_matches(db_conn, [_match(3, date(2025, 3, 7))], team_ids, venue_ids)

    assert [m.match_id for m in read_matches(db_conn)] == ["afltables-3"]


def test_save_elo_run_replaces_its_own_rows_and_keeps_other_runs(db_conn):
    team_ids, venue_ids = sync_reference_data(db_conn)
    matches = [_match(1, date(2024, 3, 7)), _match(2, date(2024, 3, 14), home="GWS", away="Sydney")]
    replace_matches(db_conn, matches, team_ids, venue_ids)
    history = build_history(read_matches(db_conn), EloConfig())

    first_id = save_elo_run(db_conn, "tier0", EloConfig(), history)
    again_id = save_elo_run(db_conn, "tier0", EloConfig(), history)
    save_elo_run(db_conn, "other", EloConfig(k_early=40.0), history)

    assert first_id == again_id
    assert _count(db_conn, "elo_runs") == 2
    assert _count(db_conn, "elo_ratings") == 4
    with db_conn.cursor() as cur:
        cur.execute("""SELECT r.expected_home_win_prob FROM elo_ratings r JOIN elo_runs e ON e.id = r.run_id
                       WHERE e.name = 'tier0' ORDER BY r.match_id""")
        assert [p for (p,) in cur.fetchall()] == pytest.approx(list(history["expected_home_win_prob"]))
        cur.execute("SELECT config->>'k_early' FROM elo_runs WHERE name = 'other'")
        assert cur.fetchone()[0] == "40.0"


def test_rebuilding_matches_clears_elo_ratings(db_conn):
    team_ids, venue_ids = sync_reference_data(db_conn)
    matches = [_match(1, date(2024, 3, 7))]
    replace_matches(db_conn, matches, team_ids, venue_ids)
    save_elo_run(db_conn, "tier0", EloConfig(), build_history(matches, EloConfig()))

    replace_matches(db_conn, matches, team_ids, venue_ids)

    assert _count(db_conn, "elo_ratings") == 0   # cascade: Elo must be recomputed after a load
    assert _count(db_conn, "elo_runs") == 1


def test_read_raw_results_feeds_the_adapter(db_conn):
    with db_conn, db_conn.cursor() as cur:
        cur.execute("""
            INSERT INTO raw_afltables_results (game, date, season, round, round_type, round_number,
                home_team, home_goals, home_behinds, home_points, away_team, away_goals, away_behinds,
                away_points, venue, margin)
            VALUES (100, '2024-03-07', 2024, 'R1', 'Regular', 1, 'Sydney', 15, 10, 100,
                    'Hawthorn', 8, 6, 54, 'S.C.G.', 46),
                   (101, '2026-08-28', 2026, 'WF', 'Regular', NULL, 'Geelong', 10, 10, 70,
                    'Carlton', 9, 9, 63, 'M.C.G.', 7)
        """)

    raw = read_raw_results(db_conn)
    matches = afltables_to_matches(raw)

    assert list(raw.columns[:3]) == ["Game", "Date", "Season"]
    assert [(m.match_id, m.round_number, m.is_final, m.round_code) for m in matches] == [
        ("afltables-100", 0, False, "R1"),     # 2024 Opening Round
        ("afltables-101", 1, True, "WF"),      # Wildcard: a final, round = last H&A round (0) + 1
    ]
