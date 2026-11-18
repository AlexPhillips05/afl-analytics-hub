"""Report how informative each Layer 2 feature is, on development seasons only (2010-2021).

For each feature: coverage, correlation with the home margin, and correlation with the margin LEFT
after Elo (residual of a linear fit on elo_diff + vai_diff) - i.e. what the feature adds beyond Elo.
The 2022+ holdout is never touched. A guide for the XGBoost branch, not a selection step.

Usage (from the repo root, data_pipeline venv active; after load_team_stats.py):
    python data_pipeline/report_features.py
"""
import sys
from contextlib import closing

import numpy as np
import pandas as pd

from db.connection import connect
from db.matches import read_matches
from db.team_stats import read_team_stats
from elo.tuned import TUNED_CONFIG
from elo.tuning import scored_mask
from features.build import build_features, feature_columns

DEV_FIRST, DEV_LAST = 2010, 2021


def feature_report(features: pd.DataFrame) -> pd.DataFrame:
    dev = features[scored_mask(features, DEV_FIRST, DEV_LAST)]
    margin = dev["target_home_margin"].astype(float)
    elo_fit = np.linalg.lstsq(
        np.column_stack([np.ones(len(dev)), dev["elo_diff"], dev["vai_diff"]]), margin, rcond=None)[0]
    residual = margin - (elo_fit[0] + elo_fit[1] * dev["elo_diff"] + elo_fit[2] * dev["vai_diff"])
    rows = []
    for col in feature_columns(features):
        x = dev[col].astype(float)
        rows.append({"feature": col, "coverage": x.notna().mean(),
                     "corr_margin": x.corr(margin), "corr_after_elo": x.corr(residual)})
    report = pd.DataFrame(rows)
    return report.reindex(report["corr_after_elo"].abs().sort_values(ascending=False).index).reset_index(drop=True)


def main() -> int:
    with closing(connect()) as conn:  # db functions manage their own transactions
        matches = read_matches(conn)
        team_stats = read_team_stats(conn)
    if not matches or team_stats.empty:
        print("Need matches and team stats: run load_matches.py and load_team_stats.py first.", file=sys.stderr)
        return 1
    features = build_features(matches, team_stats, TUNED_CONFIG)
    dev_games = int(scored_mask(features, DEV_FIRST, DEV_LAST).sum())
    print(f"Layer 2 features: {len(feature_columns(features))} columns x {len(features)} matches")
    print(f"Report on {dev_games} scored games, {DEV_FIRST}-{DEV_LAST} (excl. 2020 and 2016 Essendon games); holdout untouched\n")
    print(feature_report(features).to_string(index=False, float_format=lambda x: f"{x:+.3f}"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
