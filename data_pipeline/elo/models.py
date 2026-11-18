from dataclasses import dataclass
from datetime import date as Date


@dataclass(frozen=True)
class MatchResult:
    season: int
    round_number: int  # 0 = Opening Round (2024+); finals flagged via is_final, not a round number
    is_final: bool
    home_team: str
    away_team: str
    home_goals: int
    home_behinds: int
    away_goals: int
    away_behinds: int

    # Optional now so synthetic test fixtures stay short; ingestion should always populate them.
    # date: used by EloEngine to reject out-of-order input (leakage guard) and later for rest/bye.
    # venue: needed by the Venue Adjustment Index (feature/elo-venue-hga).
    # match_id: stable key for joining back to the database.
    match_id: str | None = None
    date: Date | None = None
    venue: str | None = None
    round_code: str | None = None  # original source code, e.g. "R1", "WF", "GF" (stored in the database)

    @property
    def home_score(self) -> int:
        return self.home_goals * 6 + self.home_behinds  # goal = 6pts, behind = 1pt

    @property
    def away_score(self) -> int:
        return self.away_goals * 6 + self.away_behinds

    @property
    def home_scoring_shots(self) -> int:
        # "Scoring shots" (goals + behinds) is the input to the scoring-shot
        # adjustment in elo/scoring.py — final score alone overstates the
        # signal since conversion accuracy is partially random.
        return self.home_goals + self.home_behinds

    @property
    def away_scoring_shots(self) -> int:
        return self.away_goals + self.away_behinds
