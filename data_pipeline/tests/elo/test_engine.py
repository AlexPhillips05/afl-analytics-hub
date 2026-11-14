from datetime import date

import pytest

from elo.config import EloConfig
from elo.engine import EloEngine
from elo.models import MatchResult


def _match(season, round_number, home, away, hg, hb, ag, ab, match_date=None):
    return MatchResult(
        season=season, round_number=round_number, is_final=False,
        home_team=home, away_team=away,
        home_goals=hg, home_behinds=hb, away_goals=ag, away_behinds=ab,
        date=match_date,
    )


def test_new_team_starts_at_initial_rating():
    engine = EloEngine()
    assert engine.get_rating("Sydney") == 1500.0


def test_single_match_updates_ratings_symmetrically_and_matches_hand_computed_values():
    engine = EloEngine()
    match = _match(2024, 1, "Home", "Away", 15, 10, 8, 6)

    result = engine.process_matches([match])

    assert len(result) == 1
    row = result.iloc[0]

    assert row["home_rating_pre"] == pytest.approx(1500.0)
    assert row["away_rating_pre"] == pytest.approx(1500.0)
    assert row["expected_home_win_prob"] == pytest.approx(0.5)
    # First season seen -> no completed prior season -> fallback conversion 0.50
    assert row["league_avg_conversion"] == pytest.approx(0.50)
    # 0.65*(25*3.5) + 0.35*100 - (0.65*(14*3.5) + 0.35*54)
    assert row["adjusted_margin"] == pytest.approx(41.125)
    # 1 / (1 + exp(-41.125 / 6)) — a ~7-goal adjusted win is almost a full win
    assert row["actual_home_outcome"] == pytest.approx(0.9989460614802479)
    assert row["rating_change"] == pytest.approx(45.835566894022435)
    assert row["home_rating_post"] == pytest.approx(1545.8355668940223)
    assert row["away_rating_post"] == pytest.approx(1454.1644331059777)

    # engine state reflects the update for subsequent matches
    assert engine.get_rating("Home") == pytest.approx(1545.8355668940223)
    assert engine.get_rating("Away") == pytest.approx(1454.1644331059777)


def test_draw_between_equal_teams_produces_zero_rating_change():
    engine = EloEngine()
    result = engine.process_matches([_match(2024, 1, "Home", "Away", 10, 5, 10, 5)])

    assert result.iloc[0]["rating_change"] == pytest.approx(0.0)


def test_favourite_loses_rating_when_held_to_a_draw():
    engine = EloEngine()
    engine.ratings = {"Home": 1600.0, "Away": 1400.0}

    result = engine.process_matches([_match(2024, 1, "Home", "Away", 10, 5, 10, 5)])

    assert result.iloc[0]["rating_change"] == pytest.approx(-4.658567155040705)


def test_outcome_is_judged_on_adjusted_margin_not_scoreboard():
    # Home wins the scoreboard 12.2 (74) to 9.14 (68) but has 14 shots to 23,
    # so on adjusted margin it was outplayed and is rated as the loser.
    engine = EloEngine()
    result = engine.process_matches([_match(2024, 1, "Home", "Away", 12, 2, 9, 14)])

    row = result.iloc[0]
    assert row["adjusted_margin"] == pytest.approx(-18.375)
    assert row["actual_home_outcome"] == pytest.approx(0.044680870272650205)
    assert row["rating_change"] == pytest.approx(-31.060779238592733)


def test_close_games_produce_small_symmetric_updates():
    # 10.6 v 10.5 and 10.5 v 10.6: near-identical games either side of zero.
    # With a hard win/loss these would swing ratings ~±16; the soft outcome keeps it ~±3.
    narrow_win = EloEngine().process_matches([_match(2024, 1, "H", "A", 10, 6, 10, 5)]).iloc[0]
    narrow_loss = EloEngine().process_matches([_match(2024, 1, "H", "A", 10, 5, 10, 6)]).iloc[0]

    assert narrow_win["adjusted_margin"] == pytest.approx(2.625)
    assert narrow_win["rating_change"] == pytest.approx(3.3324399678464958)
    assert narrow_loss["rating_change"] == pytest.approx(-narrow_win["rating_change"])


def test_conversion_uses_only_completed_prior_seasons():
    engine = EloEngine()
    # 2024: 10.5 v 8.6 and 12.4 v 9.7 -> 39 goals / 61 shots
    engine.process_matches([
        _match(2024, 1, "A", "B", 10, 5, 8, 6),
        _match(2024, 2, "A", "B", 12, 4, 9, 7),
    ])
    # Next 2024 match still uses the fallback — the season isn't complete yet.
    same_season = engine.process_matches([_match(2024, 3, "A", "B", 20, 0, 1, 20)])
    assert same_season.iloc[0]["league_avg_conversion"] == pytest.approx(0.50)

    # First 2025 match sees all of 2024 (39+21 goals / 61+41 shots), nothing from 2025.
    next_season = engine.process_matches([_match(2025, 1, "A", "B", 10, 10, 10, 10)])
    assert next_season.iloc[0]["league_avg_conversion"] == pytest.approx(60 / 102)


def test_pinned_conversion_overrides_computed_value():
    engine = EloEngine(EloConfig(league_avg_conversion=0.53))
    result = engine.process_matches([_match(2024, 1, "A", "B", 10, 5, 8, 6)])

    assert result.iloc[0]["league_avg_conversion"] == pytest.approx(0.53)


def test_out_of_order_dates_are_rejected():
    engine = EloEngine()
    engine.process_matches([_match(2024, 2, "A", "B", 10, 5, 8, 6, match_date=date(2024, 3, 21))])

    with pytest.raises(ValueError):
        engine.process_matches([_match(2024, 1, "A", "B", 10, 5, 8, 6, match_date=date(2024, 3, 14))])


def test_out_of_order_seasons_are_rejected():
    engine = EloEngine()
    engine.process_matches([_match(2025, 1, "A", "B", 10, 5, 8, 6)])

    with pytest.raises(ValueError):
        engine.process_matches([_match(2024, 1, "A", "B", 10, 5, 8, 6)])


def test_season_carryover_regresses_rating_toward_mean_between_seasons():
    engine = EloEngine()
    # Two 2024 matches so "Home" finishes above 1500 heading into 2025.
    matches_2024 = [
        MatchResult(
            season=2024, round_number=1, is_final=False,
            home_team="Home", away_team="Away",
            home_goals=15, home_behinds=10, away_goals=8, away_behinds=6,
        ),
        MatchResult(
            season=2024, round_number=2, is_final=False,
            home_team="Home", away_team="Away",
            home_goals=15, home_behinds=10, away_goals=8, away_behinds=6,
        ),
    ]
    engine.process_matches(matches_2024)
    rating_end_of_2024 = engine.get_rating("Home")
    assert rating_end_of_2024 > 1500.0  # sanity check: Home should be above the mean by now

    # First 2025 match — carryover must apply before this match's pre-game rating is read.
    match_2025 = MatchResult(
        season=2025, round_number=1, is_final=False,
        home_team="Home", away_team="Third",
        home_goals=10, home_behinds=5, away_goals=10, away_behinds=5,
    )
    result = engine.process_matches([match_2025])

    expected_pre_rating = 1500.0 + 0.72 * (rating_end_of_2024 - 1500.0)
    assert result.iloc[0]["home_rating_pre"] == pytest.approx(expected_pre_rating)


def test_no_carryover_within_the_same_season():
    engine = EloEngine()
    matches = [
        MatchResult(
            season=2024, round_number=1, is_final=False,
            home_team="Home", away_team="Away",
            home_goals=15, home_behinds=10, away_goals=8, away_behinds=6,
        ),
        MatchResult(
            season=2024, round_number=2, is_final=False,
            home_team="Home", away_team="Third",
            home_goals=10, home_behinds=5, away_goals=10, away_behinds=5,
        ),
    ]
    result = engine.process_matches(matches)

    rating_after_match_1 = result.iloc[0]["home_rating_post"]
    rating_before_match_2 = result.iloc[1]["home_rating_pre"]
    # No regression applied between two matches in the same season.
    assert rating_before_match_2 == pytest.approx(rating_after_match_1)
