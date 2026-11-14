import math
from collections.abc import Sequence

import pandas as pd

from elo.config import EloConfig
from elo.k_factor import k_factor
from elo.models import MatchResult
from elo.mov import mov_multiplier
from elo.scoring import adjusted_score, conversion_rate


class EloEngine:
    def __init__(self, config: EloConfig | None = None):
        self.config = config or EloConfig()
        self.ratings: dict[str, float] = {}
        self._current_season: int | None = None
        self._last_date = None
        # Goal/shot totals: completed seasons vs. the season in progress. The conversion
        # rate only ever uses completed seasons, so no match can see its own (or a later)
        # result. State persists across process_matches calls, so batching doesn't matter.
        self._prior_goals = 0
        self._prior_shots = 0
        self._season_goals = 0
        self._season_shots = 0

    def get_rating(self, team: str) -> float:
        return self.ratings.get(team, self.config.initial_rating)

    @property
    def league_avg_conversion(self) -> float:
        if self.config.league_avg_conversion is not None:
            return self.config.league_avg_conversion
        return conversion_rate(self._prior_goals, self._prior_shots, self.config.fallback_conversion)

    def _start_season(self, season: int) -> None:
        if self._current_season is None or season == self._current_season:
            return
        self._prior_goals += self._season_goals
        self._prior_shots += self._season_shots
        self._season_goals = 0
        self._season_shots = 0
        # Season carryover: keep `carryover` of each team's deviation from the mean,
        # regress the rest — applied before the new season's first pre-game rating is read.
        for team, rating in list(self.ratings.items()):
            deviation = rating - self.config.initial_rating
            self.ratings[team] = self.config.initial_rating + self.config.carryover * deviation

    def process_matches(self, matches: Sequence[MatchResult]) -> pd.DataFrame:
        rows = []
        for match in matches:
            # The engine trusts input order (it never sorts) but refuses input that
            # visibly goes backwards — processing out of order would leak future results.
            if self._current_season is not None and match.season < self._current_season:
                raise ValueError(f"Match out of order: season {match.season} after {self._current_season}")
            if match.date is not None:
                if self._last_date is not None and match.date < self._last_date:
                    raise ValueError(f"Match out of order: {match.date} after {self._last_date}")
                self._last_date = match.date
            self._start_season(match.season)
            self._current_season = match.season

            home_rating = self.get_rating(match.home_team)
            away_rating = self.get_rating(match.away_team)
            elo_diff = home_rating - away_rating
            expected_home = 1 / (1 + 10 ** (-elo_diff / 400))

            conversion = self.league_avg_conversion
            adj_home = adjusted_score(
                match.home_scoring_shots, match.home_score, conversion,
                self.config.scoring_shot_weight, self.config.actual_score_weight,
            )
            adj_away = adjusted_score(
                match.away_scoring_shots, match.away_score, conversion,
                self.config.scoring_shot_weight, self.config.actual_score_weight,
            )
            adjusted_margin = adj_home - adj_away

            # Outcome is judged on adjusted margin (not the scoreboard) and is continuous:
            # a logistic of the margin rather than a hard 1/0.5/0, so near-identical close
            # games produce near-identical updates. The scoreboard's influence is set by
            # actual_score_weight inside the adjusted margin, not by a separate W/L rule.
            actual_home = 1 / (1 + math.exp(-adjusted_margin / self.config.outcome_scale))

            multiplier = mov_multiplier(adjusted_margin, elo_diff, self.config)
            k = k_factor(match.round_number, match.is_final, self.config)
            rating_change = k * multiplier * (actual_home - expected_home)

            new_home_rating = home_rating + rating_change
            new_away_rating = away_rating - rating_change
            self.ratings[match.home_team] = new_home_rating
            self.ratings[match.away_team] = new_away_rating

            # Counted only after this match is rated, and only feeds the conversion rate
            # once the season is complete.
            self._season_goals += match.home_goals + match.away_goals
            self._season_shots += match.home_scoring_shots + match.away_scoring_shots

            rows.append({
                "match_id": match.match_id,
                "season": match.season,
                "round_number": match.round_number,
                "is_final": match.is_final,
                "home_team": match.home_team,
                "away_team": match.away_team,
                "home_rating_pre": home_rating,
                "away_rating_pre": away_rating,
                "home_rating_post": new_home_rating,
                "away_rating_post": new_away_rating,
                "expected_home_win_prob": expected_home,
                "league_avg_conversion": conversion,
                "adjusted_margin": adjusted_margin,
                "actual_home_outcome": actual_home,
                "rating_change": rating_change,
            })

        return pd.DataFrame(rows)
