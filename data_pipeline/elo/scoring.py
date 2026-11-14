def conversion_rate(goals: int, scoring_shots: int, fallback: float) -> float:
    # Plain goals / scoring-shots helper. The engine decides WHICH totals to pass
    # (completed prior seasons only) so no match can see its own or later results.
    if scoring_shots == 0:
        return fallback
    return goals / scoring_shots


def expected_points_per_shot(league_avg_conversion: float) -> float:
    # Converts a goal-conversion fraction into points per shot (goal = 6, behind = 1),
    # so the shot-based term below is in points, the same unit as actual_score.
    return league_avg_conversion * 6 + (1 - league_avg_conversion) * 1


def adjusted_score(
    scoring_shots: int,
    actual_score: int,
    league_avg_conversion: float,
    scoring_shot_weight: float,
    actual_score_weight: float,
) -> float:
    # Blend of "what an average-accuracy team would have scored from these shots"
    # and the real score: accuracy is partly skill, partly noise.
    pts_per_shot = expected_points_per_shot(league_avg_conversion)
    return scoring_shot_weight * (scoring_shots * pts_per_shot) + actual_score_weight * actual_score
