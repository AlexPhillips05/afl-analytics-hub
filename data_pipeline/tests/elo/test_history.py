from elo.config import EloConfig
from elo.history import build_history
from elo.models import MatchResult


def test_build_history_adds_scores_by_match_id_in_engine_order():
    matches = [
        MatchResult(season=2024, round_number=1, is_final=False, home_team="A", away_team="B",
                    home_goals=15, home_behinds=10, away_goals=8, away_behinds=6, match_id="m1"),
        MatchResult(season=2024, round_number=2, is_final=False, home_team="B", away_team="A",
                    home_goals=9, home_behinds=9, away_goals=10, away_behinds=2, match_id="m2"),
    ]

    history = build_history(matches, EloConfig())

    assert list(history["match_id"]) == ["m1", "m2"]
    assert list(history["home_score"]) == [100, 63]
    assert list(history["away_score"]) == [54, 62]
    assert "expected_home_win_prob" in history.columns
