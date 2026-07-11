from dataclasses import dataclass


@dataclass(frozen=True)
class EloConfig:
    """Tier-0 placeholder constants.

    Independently reasoned starting values, not empirically fit — see
    docs/superpowers/specs/2026-07-11-elo-engine-differentiation-design.md.
    Real calibration happens on feature/elo-optimisation.
    """

    initial_rating: float = 1500.0

    # Season carryover: ratings regress toward initial_rating between seasons
    # rather than persisting fully — high carryover (vs. a generic sports-Elo
    # default) reflects low AFL list turnover between seasons.
    carryover: float = 0.72  # fraction of deviation from initial_rating that persists across seasons

    # K-factor continuous decay: K(round) = k_late + (k_early - k_late) * exp(-round / tau).
    # Ratings react fastest early in the season (off-season roster/coaching
    # uncertainty) and settle as the season progresses.
    k_early: float = 38.0  # K at round 0
    k_late: float = 22.0   # K once ratings have converged (~round 20-21)
    tau: float = 7.0       # decay rate
    finals_k: float = 34.0  # fixed, not part of the decay curve — finals have small sample sizes per team

    # Scoring shots adjustment: blends an expected-points figure (scoring
    # shots * league conversion rate) with the actual score, since conversion
    # accuracy is partially random and shouldn't fully drive rating changes.
    scoring_shot_weight: float = 0.65
    actual_score_weight: float = 0.35
    league_avg_conversion: float | None = None  # None => computed from the matches passed to the engine
    fallback_conversion: float = 0.50  # used only if league_avg_conversion is None and no matches are given

    # MoV dampening + autocorrelation correction:
    # mov_multiplier = ln(1 + margin / mov_scale) / (1 + mov_correction * abs(elo_diff))
    # Diminishing returns on margin size, and a correction so an "expected"
    # blowout (large pre-game rating gap) moves ratings less than an upset
    # margin of the same size.
    mov_scale: float = 6.0       # AFL goal value — scales margin into goals-equivalent units
    mov_correction: float = 0.0012  # autocorrelation correction strength
