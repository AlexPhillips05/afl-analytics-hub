"""Tuned Elo settings (Tier-1), produced by data_pipeline/tune_elo.py on 2026-11-18.

Provenance:
- Objective: mean bits per game. Scored games exclude all of 2020 and 2016 games involving Essendon;
  2000-2009 are warm-up only.
- Stage A: tuned on 2010-2021, then scored once on the 2022-2026 holdout (1,073 games):
  bits/game 0.1713 (Tier-0) -> 0.1805, tipping 69.1% -> 70.3%, home bias +0.021 -> +0.019. Verdict: ADOPT.
  These holdout figures are the honest performance estimate.
- Stage B (these values): re-tuned on 2010-2026, starting from Stage A. No setting moved more than one grid
  position from Stage A, so there's no sign of recent drift. The 2027 season is the first unseen test.

Settings not listed here keep their Tier-0 defaults from EloConfig (k_early etc. are documented there).
mov_correction=0 and vai_carryover=1.0 sit at natural limits: the autocorrelation correction is switched off,
and venue tweaks no longer fade between seasons.
"""
from elo.config import EloConfig

TUNED_CONFIG = EloConfig(
    carryover=0.8,
    k_early=88.0,
    k_late=26.0,
    tau=2.0,
    scoring_shot_weight=0.8,
    actual_score_weight=0.2,
    mov_scale=4.5,
    mov_correction=0.0,
    outcome_scale=18.0,
    home_state_bonus=55.0,
    vai_learning_rate=0.075,
    vai_carryover=1.0,
)
