from elo.models import MatchResult


def test_match_result_derives_score_and_scoring_shots():
    match = MatchResult(
        season=2024,
        round_number=1,
        is_final=False,
        home_team="Sydney",
        away_team="Hawthorn",
        home_goals=15,
        home_behinds=10,
        away_goals=8,
        away_behinds=6,
    )

    assert match.home_score == 100  # 15*6 + 10
    assert match.away_score == 54   # 8*6 + 6
    assert match.home_scoring_shots == 25
    assert match.away_scoring_shots == 14
