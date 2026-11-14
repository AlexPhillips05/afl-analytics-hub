from elo.config import EloConfig
from elo.venues import team_state, venue_state


class VenueAdjustment:
    """Venue Adjustment Index: VAI(team, venue) = base value + learned per-pair tweak."""

    def __init__(self, config: EloConfig):
        self.config = config
        self.tweaks: dict[tuple[str, str], float] = {}

    def base(self, team: str, venue: str, is_home: bool) -> float:
        value = self.config.home_label_bonus if is_home else 0.0
        if venue_state(venue) == team_state(team):
            value += self.config.home_state_bonus
        return value

    def value(self, team: str, venue: str, is_home: bool) -> float:
        return self.base(team, venue, is_home) + self.tweaks.get((team, venue), 0.0)

    def update(self, home_team: str, away_team: str, venue: str, rating_change: float) -> None:
        # rating_change is from the home team's perspective (as in EloEngine), so the
        # home team's tweak moves with it and the away team's moves against it.
        step = self.config.vai_learning_rate * rating_change
        self.tweaks[(home_team, venue)] = self.tweaks.get((home_team, venue), 0.0) + step
        self.tweaks[(away_team, venue)] = self.tweaks.get((away_team, venue), 0.0) - step

    def start_new_season(self) -> None:
        for key, tweak in self.tweaks.items():
            self.tweaks[key] = self.config.vai_carryover * tweak
