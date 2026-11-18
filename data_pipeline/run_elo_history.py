"""Run the Elo engine over all AFL Tables results and print a sanity-check report.

Runs twice, Tier-0 defaults vs TUNED_CONFIG, compares them, and saves both runs to the database
(elo_runs / elo_ratings, as "tier0" and "tuned").

Usage (from the repo root, data_pipeline venv active; after load_matches.py):
    python data_pipeline/run_elo_history.py
"""
import sys
from contextlib import closing

import pandas as pd

from db.connection import connect
from db.elo_store import save_elo_run
from db.matches import read_matches
from elo.config import EloConfig
from elo.evaluation import WARM_UP_LAST_SEASON, end_of_season_ratings, season_metrics
from elo.history import build_history
from elo.tuned import TUNED_CONFIG

SUMMARY_COLUMNS = ["tip_accuracy", "home_baseline_accuracy", "bits_per_game", "home_bias", "mean_abs_rating_change"]


def evaluated_averages(history: pd.DataFrame) -> pd.Series:
    metrics = season_metrics(history)
    return metrics.loc[metrics["season"] > WARM_UP_LAST_SEASON, SUMMARY_COLUMNS].mean()


def format_report(tuned: pd.DataFrame, tier0: pd.DataFrame) -> str:
    metrics = season_metrics(tuned)
    lines = ["Per-season metrics (Tuned)",
             metrics.to_string(index=False, float_format=lambda x: f"{x:.3f}"), ""]

    evaluated = metrics[metrics["season"] > WARM_UP_LAST_SEASON]
    comparison = pd.DataFrame({"Tier-0": evaluated_averages(tier0), "Tuned": evaluated_averages(tuned)})
    comparison["change"] = comparison["Tuned"] - comparison["Tier-0"]
    lines.append(f"Averages {int(evaluated['season'].min())}-{int(evaluated['season'].max())} "
                 f"(excluding warm-up; 2020 included but flagged):")
    lines.append(comparison.to_string(float_format=lambda x: f"{x:.3f}"))
    lines.append("Note: Tuned was fitted on these seasons, so its averages are in-sample. The honest estimate is the")
    lines.append("2022+ holdout result from tune_elo.py (recorded in elo/tuned.py).")
    lines.append("")

    lines.append("End-of-season top 3 / bottom 3 (Tuned)")
    for season, group in end_of_season_ratings(tuned).groupby("season"):
        ranked = group.sort_values("rating", ascending=False)
        top = ", ".join(f"{t} {r:.0f}" for t, r in zip(ranked["team"].head(3), ranked["rating"].head(3)))
        bottom = ", ".join(f"{t} {r:.0f}" for t, r in zip(ranked["team"].tail(3), ranked["rating"].tail(3)))
        lines.append(f"  {season}  top: {top}  |  bottom: {bottom}")
    return "\n".join(lines)


def main() -> int:
    with closing(connect()) as conn:  # db functions manage their own transactions
        matches = read_matches(conn)
        if not matches:
            print("No matches in the database. Run fetch_results.R, then load_matches.py.", file=sys.stderr)
            return 1
        tier0 = build_history(matches, EloConfig())
        tuned = build_history(matches, TUNED_CONFIG)
        save_elo_run(conn, "tier0", EloConfig(), tier0)
        save_elo_run(conn, "tuned", TUNED_CONFIG, tuned)
    print(format_report(tuned, tier0))
    print(f"\nSaved Elo runs 'tier0' and 'tuned' ({len(tuned)} matches each) to the database")
    return 0


if __name__ == "__main__":
    sys.exit(main())
