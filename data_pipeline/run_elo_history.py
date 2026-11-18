"""Run the Elo engine over all AFL Tables results and print a sanity-check report.

Runs twice, Tier-0 defaults vs TUNED_CONFIG, and compares them.

Usage (from the repo root, data_pipeline venv active):
    Rscript data_pipeline/fetch_results.R      # once, to create the CSV
    python data_pipeline/run_elo_history.py
"""
import sys
from pathlib import Path

import pandas as pd

from elo.adapters import afltables_to_matches
from elo.config import EloConfig
from elo.evaluation import WARM_UP_LAST_SEASON, end_of_season_ratings, season_metrics
from elo.history import build_history
from elo.tuned import TUNED_CONFIG

DATA_DIR = Path(__file__).resolve().parent / "data"
RESULTS_CSV = DATA_DIR / "afltables_results.csv"
HISTORY_CSV = DATA_DIR / "elo_history.csv"

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
    if not RESULTS_CSV.exists():
        print(f"Missing {RESULTS_CSV}. Run `Rscript data_pipeline/fetch_results.R` from the repo root first.",
              file=sys.stderr)
        return 1
    matches = afltables_to_matches(pd.read_csv(RESULTS_CSV))
    tier0 = build_history(matches, EloConfig())
    tuned = build_history(matches, TUNED_CONFIG)
    tuned.to_csv(HISTORY_CSV, index=False)
    print(format_report(tuned, tier0))
    print(f"\nWrote {len(tuned)} rows (Tuned) to {HISTORY_CSV}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
