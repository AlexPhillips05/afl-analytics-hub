"""Run the Elo engine over all AFL Tables results and print a sanity-check report.

Usage (from the repo root, data_pipeline venv active):
    Rscript data_pipeline/fetch_results.R      # once, to create the CSV
    python data_pipeline/run_elo_history.py
"""
import sys
from pathlib import Path

import pandas as pd

from elo.adapters import afltables_to_matches
from elo.engine import EloEngine
from elo.evaluation import WARM_UP_LAST_SEASON, end_of_season_ratings, season_metrics

DATA_DIR = Path(__file__).resolve().parent / "data"
RESULTS_CSV = DATA_DIR / "afltables_results.csv"
HISTORY_CSV = DATA_DIR / "elo_history.csv"


def build_history(results: pd.DataFrame) -> pd.DataFrame:
    matches = afltables_to_matches(results)
    history = EloEngine().process_matches(matches)
    scores = pd.DataFrame(
        {"match_id": m.match_id, "home_score": m.home_score, "away_score": m.away_score}
        for m in matches
    )
    return history.merge(scores, on="match_id", how="left", validate="one_to_one")


def format_report(history: pd.DataFrame) -> str:
    metrics = season_metrics(history)
    lines = ["Per-season metrics", metrics.to_string(index=False, float_format=lambda x: f"{x:.3f}"), ""]

    evaluated = metrics[metrics["season"] > WARM_UP_LAST_SEASON]
    lines.append(f"Averages {int(evaluated['season'].min())}-{int(evaluated['season'].max())} "
                 f"(excluding warm-up; 2020 included but flagged):")
    for col in ["tip_accuracy", "home_baseline_accuracy", "bits_per_game", "mean_abs_rating_change"]:
        lines.append(f"  {col:<24} {evaluated[col].mean():.3f}")
    lines.append("")

    lines.append("End-of-season top 3 / bottom 3")
    for season, group in end_of_season_ratings(history).groupby("season"):
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
    history = build_history(pd.read_csv(RESULTS_CSV))
    history.to_csv(HISTORY_CSV, index=False)
    print(format_report(history))
    print(f"\nWrote {len(history)} rows to {HISTORY_CSV}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
