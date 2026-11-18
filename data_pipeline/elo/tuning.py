import dataclasses
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

import pandas as pd

from elo.config import EloConfig
from elo.evaluation import match_bits, tip_correct

COVID_SEASON = 2020
ESSENDON = "Essendon"
ESSENDON_EXCLUDED_SEASON = 2016


def _steps(start: float, stop: float, step: float, extra: Sequence[float] = ()) -> tuple[float, ...]:
    """Inclusive grid built from integer counts (no float drift), plus any extra points, sorted."""
    count = round((stop - start) / step)
    values = {float(round(start + i * step, 6)) for i in range(count + 1)} | {float(round(x, 6)) for x in extra}
    return tuple(sorted(values))


# Each grid includes the Tier-0 default (checked by tests). outcome_scale, k_early, k_late and tau
# were widened after a first run showed their best values at the original grid edges.
TUNABLE_GRIDS: dict[str, tuple[float, ...]] = {
    "carryover": _steps(0.50, 0.95, 0.05, extra=(0.72,)),
    "k_early": _steps(20, 60, 2) + _steps(64, 120, 4),
    "k_late": _steps(10, 60, 2),
    "tau": _steps(1, 14, 1),
    "finals_k": _steps(16, 50, 2),
    "scoring_shot_weight": _steps(0.30, 0.90, 0.05),
    "mov_scale": (3.0, 4.5, 6.0, 8.0, 10.0, 12.0, 15.0),
    "mov_correction": _steps(0.0, 0.003, 0.0003),
    "mov_floor": _steps(0.0, 1.5, 0.25),
    "outcome_scale": _steps(2, 16, 1) + _steps(18, 60, 2),
    "home_label_bonus": _steps(0, 50, 5),
    "home_state_bonus": _steps(0, 100, 5),
    "vai_learning_rate": _steps(0.0, 0.30, 0.025),
    "vai_carryover": _steps(0.50, 1.00, 0.05),
}


def scored_mask(history: pd.DataFrame, first_season: int, last_season: int) -> pd.Series:
    """Games that count towards the objective: in range, not 2020, not a 2016 Essendon game."""
    in_range = history["season"].between(first_season, last_season)
    covid = history["season"] == COVID_SEASON
    essendon_2016 = (history["season"] == ESSENDON_EXCLUDED_SEASON) & (
        (history["home_team"] == ESSENDON) | (history["away_team"] == ESSENDON)
    )
    return in_range & ~covid & ~essendon_2016


def mean_bits(history: pd.DataFrame, first_season: int, last_season: int) -> float:
    scored = history[scored_mask(history, first_season, last_season)]
    return sum(
        match_bits(p, h, a)
        for p, h, a in zip(scored["expected_home_win_prob"], scored["home_score"], scored["away_score"])
    ) / len(scored)


def summary(history: pd.DataFrame, first_season: int, last_season: int) -> dict[str, float]:
    """Bits, tipping accuracy and home bias over the scored games in a season range."""
    scored = history[scored_mask(history, first_season, last_season)]
    rows = list(zip(scored["expected_home_win_prob"], scored["home_score"], scored["away_score"]))
    home_result = [1.0 if h > a else 0.5 if h == a else 0.0 for _, h, a in rows]
    return {
        "games": len(rows),
        "bits_per_game": sum(match_bits(p, h, a) for p, h, a in rows) / len(rows),
        "tip_accuracy": sum(tip_correct(p, h, a) for p, h, a in rows) / len(rows),
        "home_bias": sum(r - p for r, (p, _, _) in zip(home_result, rows)) / len(rows),
    }


def with_value(config: EloConfig, name: str, value: float) -> EloConfig:
    """Return a copy of `config` with one tunable setting changed.

    scoring_shot_weight also sets actual_score_weight = 1 - weight, so the blend stays a true split.
    """
    if name not in TUNABLE_GRIDS:
        raise ValueError(f"{name!r} is not a tunable setting")
    if name == "scoring_shot_weight":
        return dataclasses.replace(config, scoring_shot_weight=value, actual_score_weight=round(1 - value, 6))
    return dataclasses.replace(config, **{name: value})


@dataclass(frozen=True)
class SearchResult:
    start_score: float
    best_config: EloConfig
    best_score: float
    passes: int
    converged: bool
    sensitivity: dict[str, tuple[float, float]]  # setting -> (min, max) score over its grid, final pass
    at_grid_edge: tuple[str, ...]


def coordinate_search(
    evaluate: Callable[[EloConfig], float],
    start: EloConfig,
    grids: Mapping[str, Sequence[float]] = TUNABLE_GRIDS,
    max_passes: int = 10,
    min_improvement: float = 1e-4,
) -> SearchResult:
    """Tune one setting at a time over its grid (others fixed), repeating passes until nothing changes.

    `evaluate` scores a config; higher is better. A new value is adopted only if it beats the
    current best by more than `min_improvement`, so noise can't cause churn.
    """
    best = start
    best_score = start_score = evaluate(start)
    passes = 0
    converged = False
    sensitivity: dict[str, tuple[float, float]] = {}

    while passes < max_passes:
        passes += 1
        changed = False
        sensitivity = {}
        for name, grid in grids.items():
            scores = {value: evaluate(with_value(best, name, value)) for value in grid}
            sensitivity[name] = (min(scores.values()), max(scores.values()))
            top_value = max(scores, key=scores.get)
            if scores[top_value] > best_score + min_improvement:
                best, best_score, changed = with_value(best, name, top_value), scores[top_value], True
        if not changed:
            converged = True
            break

    at_edge = tuple(
        name for name, grid in grids.items()
        if getattr(best, name) in (min(grid), max(grid))
    )
    return SearchResult(start_score, best, best_score, passes, converged, sensitivity, at_edge)
