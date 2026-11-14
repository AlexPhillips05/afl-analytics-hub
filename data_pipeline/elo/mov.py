import math

from elo.config import EloConfig


def mov_multiplier(margin: float, elo_diff: float, config: EloConfig) -> float:
    """margin and elo_diff are both from the home team's perspective."""
    # Re-express the rating gap from the winner's side: positive = favourite won.
    if margin > 0:
        winner_elo_diff = elo_diff
    elif margin < 0:
        winner_elo_diff = -elo_diff
    else:
        winner_elo_diff = 0.0
    # Only dampen favourite wins; upsets get the undamped multiplier. Clamping at
    # zero also keeps the denominator >= 1, so it can never blow up or flip sign.
    dampening = 1 + config.mov_correction * max(0.0, winner_elo_diff)
    # mov_floor stops draws / razor-thin margins from producing a zero multiplier.
    return (math.log(1 + abs(margin) / config.mov_scale) + config.mov_floor) / dampening
