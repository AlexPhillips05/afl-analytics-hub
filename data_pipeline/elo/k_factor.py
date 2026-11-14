import math

from elo.config import EloConfig


def k_factor(round_number: int, is_final: bool, config: EloConfig) -> float:
    # Finals use a fixed K outside the decay curve (small per-team sample, high stakes).
    if is_final:
        return config.finals_k
    # Continuous decay from k_early (round 0 = Opening Round) toward k_late.
    return config.k_late + (config.k_early - config.k_late) * math.exp(-round_number / config.tau)
