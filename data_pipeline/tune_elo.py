"""Tune EloConfig's Tier-0 constants against historical bits per game.

Stage A: tune on 2010-2021, score the 2022+ holdout once -> ADOPT or KEEP TIER-0.
Stage B (only if ADOPT): re-tune on 2010-latest for the live settings (TUNED_CONFIG).

Usage (from the repo root, data_pipeline venv active; takes a few minutes):
    python data_pipeline/tune_elo.py
"""
import json
import sys
import time
from datetime import date
from pathlib import Path

import pandas as pd

from elo.adapters import afltables_to_matches
from elo.config import EloConfig
from elo.history import build_history
from elo.tuning import TUNABLE_GRIDS, SearchResult, coordinate_search, mean_bits, summary

DATA_DIR = Path(__file__).resolve().parent / "data"
RESULTS_CSV = DATA_DIR / "afltables_results.csv"
OUTPUT_JSON = DATA_DIR / "tuned_config.json"

TUNE_FIRST, TUNE_LAST = 2010, 2021
HOLDOUT_FIRST = 2022


def tunable_values(config: EloConfig) -> dict[str, float]:
    return {name: getattr(config, name) for name in TUNABLE_GRIDS}


def format_search(title: str, result: SearchResult) -> str:
    lines = [title,
             f"  bits/game {result.start_score:.4f} -> {result.best_score:.4f} "
             f"({result.passes} passes, {'converged' if result.converged else 'NOT converged'})",
             "  Sensitivity (bits range across grid, final pass), largest first:"]
    ranked = sorted(result.sensitivity.items(), key=lambda kv: kv[1][1] - kv[1][0], reverse=True)
    for name, (lo, hi) in ranked:
        edge = "  <- at grid edge" if name in result.at_grid_edge else ""
        lines.append(f"    {name:<20} {hi - lo:.4f}   value {getattr(result.best_config, name):g}{edge}")
    return "\n".join(lines)


def format_holdout(tier0: dict, tuned: dict, first: int, last: int) -> str:
    lines = [f"Holdout {first}-{last} ({tier0['games']} scored games):",
             f"  {'':<14}{'Tier-0':>9}{'Stage A':>9}{'change':>9}"]
    for key in ["bits_per_game", "tip_accuracy", "home_bias"]:
        lines.append(f"  {key:<14}{tier0[key]:>9.4f}{tuned[key]:>9.4f}{tuned[key] - tier0[key]:>+9.4f}")
    return "\n".join(lines)


def shifted(name: str, a: float, b: float) -> bool:
    grid = TUNABLE_GRIDS[name]
    return abs(grid.index(b) - grid.index(a)) > 1


def format_drift(tier0: EloConfig, stage_a: EloConfig, stage_b: EloConfig) -> str:
    lines = ["Drift: Tier-0 vs Stage A (to 2021) vs Stage B (to latest)",
             f"  {'setting':<20}{'Tier-0':>9}{'Stage A':>9}{'Stage B':>9}"]
    for name in TUNABLE_GRIDS:
        a, b = getattr(stage_a, name), getattr(stage_b, name)
        flag = "  <- shifted" if shifted(name, a, b) else ""
        lines.append(f"  {name:<20}{getattr(tier0, name):>9g}{a:>9g}{b:>9g}{flag}")
    return "\n".join(lines)


def main() -> int:
    if not RESULTS_CSV.exists():
        print(f"Missing {RESULTS_CSV}. Run `Rscript data_pipeline/fetch_results.R` from the repo root first.",
              file=sys.stderr)
        return 1
    matches = afltables_to_matches(pd.read_csv(RESULTS_CSV))
    latest = max(m.season for m in matches)
    tier0 = EloConfig()

    def objective(first: int, last: int):
        return lambda config: mean_bits(build_history(matches, config), first, last)

    started = time.time()
    stage_a = coordinate_search(objective(TUNE_FIRST, TUNE_LAST), tier0)
    print(format_search(f"Stage A: tune {TUNE_FIRST}-{TUNE_LAST}", stage_a), "\n")

    holdout_tier0 = summary(build_history(matches, tier0), HOLDOUT_FIRST, latest)
    holdout_a = summary(build_history(matches, stage_a.best_config), HOLDOUT_FIRST, latest)
    print(format_holdout(holdout_tier0, holdout_a, HOLDOUT_FIRST, latest), "\n")

    adopt = holdout_a["bits_per_game"] > holdout_tier0["bits_per_game"]
    print("Verdict:", "ADOPT" if adopt else "KEEP TIER-0", "\n")

    output = {
        "run_date": date.today().isoformat(),
        "verdict": "ADOPT" if adopt else "KEEP TIER-0",
        "tier0": tunable_values(tier0),
        "stage_a": {"tuned_on": [TUNE_FIRST, TUNE_LAST], "values": tunable_values(stage_a.best_config),
                    "tune_bits": stage_a.best_score, "holdout": holdout_a, "holdout_tier0": holdout_tier0},
    }

    if adopt:
        stage_b = coordinate_search(objective(TUNE_FIRST, latest), stage_a.best_config)
        print(format_search(f"Stage B: re-tune {TUNE_FIRST}-{latest}", stage_b), "\n")
        print(format_drift(tier0, stage_a.best_config, stage_b.best_config), "\n")
        output["stage_b"] = {"tuned_on": [TUNE_FIRST, latest], "values": tunable_values(stage_b.best_config),
                             "tune_bits": stage_b.best_score}
        changed = {k: v for k, v in tunable_values(stage_b.best_config).items() if v != getattr(tier0, k)}
        if "scoring_shot_weight" in changed:
            changed["actual_score_weight"] = stage_b.best_config.actual_score_weight
        print("TUNED_CONFIG settings that differ from Tier-0:")
        for name, value in changed.items():
            print(f"    {name}={value!r},")

    OUTPUT_JSON.write_text(json.dumps(output, indent=2))
    print(f"\nWrote {OUTPUT_JSON} ({time.time() - started:.0f}s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
