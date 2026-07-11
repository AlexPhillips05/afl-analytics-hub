from dataclasses import dataclass


@dataclass(frozen=True)
class MatchResult:
    season: int
    round_number: int
    is_final: bool
    home_team: str
    away_team: str
    home_goals: int
    home_behinds: int
    away_goals: int
    away_behinds: int

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
