import pandas as pd

from elo.config import EloConfig
from elo.engine import EloEngine
from elo.models import MatchResult


def build_history(matches: list[MatchResult], config: EloConfig) -> pd.DataFrame:
    """Run the engine over `matches` (chronological) and add each match's scoreboard scores.

    Takes already-adapted matches so callers that run the engine many times (tuning)
    adapt the raw data only once.
    """
    history = EloEngine(config).process_matches(matches)
    scores = pd.DataFrame(
        {"match_id": m.match_id, "home_score": m.home_score, "away_score": m.away_score}
        for m in matches
    )
    return history.merge(scores, on="match_id", how="left", validate="one_to_one")
