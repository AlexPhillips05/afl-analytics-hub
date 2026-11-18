"""Train and honestly evaluate Layer 2 (Elo baseline vs Ridge vs XGBoost), then refit and save the winner.

1. Features with STAGE_A_CONFIG (no Elo setting has seen 2022+).
2. Walk-forward CV on 2010-2021 picks hyperparameters and a candidate (Ridge or XGBoost); CV gate.
3. The 2022+ holdout is scored ONCE; verdict ADOPT or KEEP ELO BASELINE.
4. The chosen model is refitted on 2010-latest with TUNED_CONFIG features and saved.

Usage (from the repo root, data_pipeline venv active; after load_team_stats.py; ~20 seconds):
    python data_pipeline/train_layer2.py
"""
import json
import sys
from contextlib import closing
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from db.connection import connect
from db.matches import read_matches
from db.team_stats import read_team_stats
from elo.tuned import STAGE_A_CONFIG, TUNED_CONFIG
from features.build import build_features
from layer2.artifact import TrainedModel, save
from layer2.calibration import fit_scale, win_prob
from layer2.estimators import MAKERS, RIDGE_GRID, XGB_GRID, model_inputs
from layer2.evaluate import RESULT, TARGET, best_params, cv_gate, holdout_verdict, score
from layer2.splits import DEV_FIRST, DEV_LAST, scored_rows, walk_forward_folds

DATA_DIR = Path(__file__).resolve().parent / "data"
MODEL_PATH = DATA_DIR / "layer2_model.joblib"
REPORT_PATH = DATA_DIR / "layer2_report.json"
GRIDS = {"baseline": [{}], "ridge": RIDGE_GRID, "xgboost": XGB_GRID}
HOLDOUT_FIRST = DEV_LAST + 1


def fit(kind: str, params: dict, features: pd.DataFrame, rows: pd.Series):
    model = MAKERS[kind](**params)
    model.fit(model_inputs(features[rows], kind), features.loc[rows, TARGET])
    return model


def table(scores: dict[str, dict]) -> str:
    lines = [f"  {'model':<16}{'games':>7}{'MAE':>9}{'tipping':>10}{'bits/game':>11}"]
    for name, s in scores.items():
        mae = f"{s['mae']:.3f}" if s.get("mae") is not None else "-"
        lines.append(f"  {name:<16}{s['games']:>7}{mae:>9}{s['tip_accuracy']:>10.4f}{s['bits_per_game']:>11.4f}")
    return "\n".join(lines)


def importances(kind: str, model, features: pd.DataFrame, top: int = 8) -> list[tuple[str, float]]:
    names = list(model_inputs(features.head(1), kind).columns)
    if kind == "ridge":
        values = model[-1].coef_                      # standardised coefficients (points per SD)
    elif kind == "xgboost":
        gain = model.get_booster().get_score(importance_type="gain")
        values = [gain.get(n, 0.0) for n in names]
    else:
        values = model.coef_
    ranked = sorted(zip(names, values), key=lambda nv: abs(nv[1]), reverse=True)
    return [(n, float(v)) for n, v in ranked[:top]]


def main() -> int:
    with closing(connect()) as conn:  # db functions manage their own transactions
        matches, team_stats = read_matches(conn), read_team_stats(conn)
    if not matches or team_stats.empty:
        print("Need matches and team stats: run load_matches.py and load_team_stats.py first.", file=sys.stderr)
        return 1
    latest = max(m.season for m in matches)

    # ---- 1-2. Walk-forward CV on development seasons (Stage A Elo features) ----
    feats = build_features(matches, team_stats, STAGE_A_CONFIG)
    folds = walk_forward_folds(feats)
    chosen, cv = {}, {}
    for kind, grid in GRIDS.items():
        params, oof, _ = best_params(kind, grid, feats, folds)
        scale = fit_scale(oof, feats.loc[oof.index, RESULT])
        chosen[kind] = {"params": params, "scale": scale}
        cv[kind] = score(oof, win_prob(oof, scale), feats)
    oof_index = oof.index
    engine = score(pd.Series(np.nan, index=oof_index), feats.loc[oof_index, "elo_home_win_prob"].to_numpy(), feats)
    engine["mae"] = None
    candidate = min(("ridge", "xgboost"), key=lambda k: cv[k]["mae"])
    passed = cv_gate(cv[candidate], cv["baseline"])

    print(f"Walk-forward CV, validation seasons {folds[0][0]}-{folds[-1][0]} (excl. 2020), Stage A Elo features")
    print(table({**cv, "elo engine (ref)": engine}))
    for kind in GRIDS:
        print(f"  {kind}: params {chosen[kind]['params']}, calibration scale s = {chosen[kind]['scale']:.2f}")
    print(f"Candidate: {candidate}. CV gate (beats baseline MAE, bits not worse): {'PASS' if passed else 'FAIL'}\n")

    # ---- 3. Holdout, scored once ----
    dev = scored_rows(feats, DEV_FIRST, DEV_LAST)
    hold = scored_rows(feats, HOLDOUT_FIRST, latest)
    holdout, dev_models = {}, {}
    for kind in GRIDS:
        dev_models[kind] = fit(kind, chosen[kind]["params"], feats, dev)
        pred = pd.Series(dev_models[kind].predict(model_inputs(feats[hold], kind)), index=feats.index[hold])
        holdout[kind] = score(pred, win_prob(pred, chosen[kind]["scale"]), feats)
    hold_engine = score(pd.Series(np.nan, index=feats.index[hold]), feats.loc[hold, "elo_home_win_prob"].to_numpy(), feats)
    hold_engine["mae"] = None
    verdict = holdout_verdict(passed, holdout[candidate], holdout["baseline"])
    print(f"Holdout {HOLDOUT_FIRST}-{latest} (scored once; models trained on {DEV_FIRST}-{DEV_LAST})")
    print(table({**holdout, "elo engine (ref)": hold_engine}))
    print(f"Verdict: {verdict}\n")

    for kind in ("ridge", "xgboost"):
        label = "standardised coefficients" if kind == "ridge" else "gain importance"
        print(f"{kind} {label} (trained {DEV_FIRST}-{DEV_LAST}):")
        for name, value in importances(kind, dev_models[kind], feats):
            print(f"    {name:<30}{value:+10.2f}")
    print()

    # ---- 4. Final refit on all seasons with TUNED_CONFIG features ----
    final_kind = candidate if verdict == "ADOPT" else "baseline"
    final_feats = build_features(matches, team_stats, TUNED_CONFIG)
    all_rows = scored_rows(final_feats, DEV_FIRST, latest)
    estimator = fit(final_kind, chosen[final_kind]["params"], final_feats, all_rows)
    model = TrainedModel(kind=final_kind, estimator=estimator,
                         feature_names=list(model_inputs(final_feats.head(1), final_kind).columns),
                         scale=chosen[final_kind]["scale"], elo_config_name="TUNED_CONFIG",
                         trained_seasons=(DEV_FIRST, latest), params=chosen[final_kind]["params"])
    save(model, MODEL_PATH)
    REPORT_PATH.write_text(json.dumps({
        "run_date": date.today().isoformat(), "verdict": verdict, "candidate": candidate, "cv_gate_passed": passed,
        "final_model": final_kind, "chosen": chosen, "cv": cv, "holdout": holdout,
        "holdout_seasons": [HOLDOUT_FIRST, latest],
    }, indent=2))
    print(f"Final model: {final_kind} refitted on {DEV_FIRST}-{latest} ({int(all_rows.sum())} games, TUNED_CONFIG features)")
    print(f"Saved {MODEL_PATH} and {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
