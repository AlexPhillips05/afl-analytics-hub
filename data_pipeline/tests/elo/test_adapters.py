from datetime import date

import pandas as pd
import pytest

from elo.adapters import afltables_to_matches


def _row(game, match_date, season, round_code, home="Sydney", away="Hawthorn",
         hg=15, hb=10, ag=8, ab=6, venue="S.C.G."):
    # Mirrors the raw fitzRoy::fetch_results_afltables() columns the adapter reads.
    return {
        "Game": game, "Date": match_date, "Round": round_code, "Season": season,
        "Home.Team": home, "Home.Goals": hg, "Home.Behinds": hb,
        "Away.Team": away, "Away.Goals": ag, "Away.Behinds": ab,
        "Venue": venue,
    }


def test_maps_fields_and_types():
    df = pd.DataFrame([_row(100, "2023-03-16", 2023.0, "R1")])

    [match] = afltables_to_matches(df)

    assert match.season == 2023
    assert isinstance(match.season, int)
    assert match.round_number == 1
    assert match.is_final is False
    assert match.home_team == "Sydney"
    assert match.away_team == "Hawthorn"
    assert (match.home_goals, match.home_behinds, match.away_goals, match.away_behinds) == (15, 10, 8, 6)
    assert match.date == date(2023, 3, 16)
    assert match.venue == "S.C.G."
    assert match.match_id == "afltables-100"
    assert match.round_code == "R1"


def test_opening_round_shift_applies_from_2024_only():
    df = pd.DataFrame([
        _row(1, "2023-03-16", 2023, "R1"),
        _row(2, "2023-03-23", 2023, "R2"),
        _row(3, "2024-03-07", 2024, "R1"),  # Opening Round
        _row(4, "2024-03-14", 2024, "R2"),  # official Round 1
    ])

    rounds = [m.round_number for m in afltables_to_matches(df)]

    assert rounds == [1, 2, 0, 1]


def test_finals_codes_including_wildcard_are_finals_after_last_home_away_round():
    df = pd.DataFrame([
        _row(1, "2026-08-20", 2026, "R25"),  # last H&A round -> official round 24
        _row(2, "2026-08-28", 2026, "WF"),
        _row(3, "2026-09-04", 2026, "QF"),
        _row(4, "2026-09-05", 2026, "EF"),
        _row(5, "2026-09-11", 2026, "SF"),
        _row(6, "2026-09-18", 2026, "PF"),
        _row(7, "2026-09-26", 2026, "GF"),
    ])

    matches = afltables_to_matches(df)

    assert matches[0].is_final is False
    assert matches[0].round_number == 24
    for final in matches[1:]:
        assert final.is_final is True
        assert final.round_number == 25


def test_output_is_sorted_by_date_then_game():
    df = pd.DataFrame([
        _row(12, "2025-08-27", 2025, "R1"),  # postponed Opening Round match
        _row(11, "2025-03-07", 2025, "R1"),
        _row(21, "2025-03-13", 2025, "R2"),
        _row(20, "2025-03-13", 2025, "R2"),  # same day: lower Game number first
    ])

    ids = [m.match_id for m in afltables_to_matches(df)]

    assert ids == ["afltables-11", "afltables-20", "afltables-21", "afltables-12"]


def test_unknown_round_code_raises():
    df = pd.DataFrame([_row(1, "2025-03-07", 2025, "XF")])

    with pytest.raises(ValueError, match="XF"):
        afltables_to_matches(df)
