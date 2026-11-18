"""Train and honestly evaluate Layer 2, then refit and save the result.

The margin model and the win-probability source are chosen separately:
- Margin: Elo baseline vs Ridge vs XGBoost. The candidate (lower CV MAE of Ridge/XGBoost) is adopted only if it beats
  the baseline in walk-forward CV by at least MIN_Z standard errors (paired, per game) AND is lower on holdout MAE.
- Probability: the Elo engine's own probability by default. The challenger (best CV bits among the margin models'
  logistic curves) is adopted only if it beats the engine on bits in CV AND on the holdout.

1. Features with STAGE_A_CONFIG (no Elo setting has seen 2022+).
2. Walk-forward CV on 2010-2021 picks hyperparameters, calibration scales, the margin candidate and the probability challenger.
3. The 2022+ holdout is scored once per decision round (see HOLDOUT_LOOKS); both verdicts.
4. The chosen models are refitted on 2010-latest with TUNED_CONFIG features and saved.

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
from layer2.artifact import ELO_PROB_COLUMN, TrainedModel, save
from layer2.calibration import fit_scale, win_prob
from layer2.estimators import MAKERS, RIDGE_GRID, XGB_GRID, model_inputs
from layer2.evaluate import (MIN_Z, RESULT, TARGET, best_params, margin_cv_gate, margin_gate, paired_mae_diff,
                             prob_gate, score)
from layer2.splits import DEV_FIRST, DEV_LAST, scored_rows, walk_forward_folds

DATA_DIR = Path(__file__).resolve().parent / "data"
MODEL_PATH = DATA_DIR / "layer2_model.joblib"
REPORT_PATH = DATA_DIR / "layer2_report.json"
GRIDS = {"baseline": [{}], "ridge": RIDGE_GRID, "xgboost": XGB_GRID}
HOLDOUT_FIRST = DEV_LAST + 1
# Times the 2022+ holdout has informed a decision: 1 = xgboost-model, 2 = versus-elo-expectation.
# Every look leaks a little; once feature work continues past this, the next unseen season is the real test.
HOLDOUT_LOOKS = 2
ENGINE = "elo engine"


def input_names(kind: str, features: pd.DataFrame) -> list[str]:
    return list(model_inputs(features.head(1), kind).columns)


def fit(kind: str, params: dict, features: pd.DataFrame, rows: pd.Series):
    model = MAKERS[kind](**params)
    model.fit(model_inputs(features[rows], kind), features.loc[rows, TARGET])
    return model


def engine_score(features: pd.DataFrame, index: pd.Index) -> dict:
    s = score(pd.Series(np.nan, index=index), features.loc[index, ELO_PROB_COLUMN].to_numpy(), features)
    s["mae"] = None
    return s


def table(scores: dict[str, dict]) -> str:
    lines = [f"  {'model':<16}{'games':>7}{'MAE':>9}{'tipping':>10}{'bits/game':>11}"]
    for name, s in scores.items():
        mae = f"{s['mae']:.3f}" if s.get("mae") is not None else "-"
        lines.append(f"  {name:<16}{s['games']:>7}{mae:>9}{s['tip_accuracy']:>10.4f}{s['bits_per_game']:>11.4f}")
    return "\n".join(lines)


def importances(kind: str, model, features: pd.DataFrame, top: int = 8) -> list[tuple[str, float]]:
    names = input_names(kind, features)
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
    chosen, cv, oofs = {}, {}, {}
    for kind, grid in GRIDS.items():
        params, oof, _ = best_params(kind, grid, feats, folds)
        oofs[kind] = oof
        scale = fit_scale(oof, feats.loc[oof.index, RESULT])
        chosen[kind] = {"params": params, "scale": scale}
        cv[kind] = score(oof, win_prob(oof, scale), feats)
    cv[ENGINE] = engine_score(feats, oof.index)
    candidate = min(("ridge", "xgboost"), key=lambda k: cv[k]["mae"])
    challenger = max(GRIDS, key=lambda k: cv[k]["bits_per_game"])
    margin_cv = margin_cv_gate(oofs[candidate], oofs["baseline"], feats)
    diff, se = paired_mae_diff(oofs[candidate], oofs["baseline"], feats)
    prob_cv = prob_gate(cv[challenger], cv[ENGINE])

    print(f"Walk-forward CV, validation seasons {folds[0][0]}-{folds[-1][0]} (excl. 2020), Stage A Elo features")
    print("  (bits/tipping for models = their margin curve; the Elo engine row is the default probability source)")
    print(table(cv))
    for kind in GRIDS:
        print(f"  {kind}: params {chosen[kind]['params']}, calibration scale s = {chosen[kind]['scale']:.2f}")
    print(f"Margin candidate: {candidate}. MAE vs baseline {diff:+.3f} (SE {se:.3f}, z {diff / se:+.2f}). "
          f"CV gate (better by >= {MIN_Z:g} SE): {'PASS' if margin_cv else 'FAIL'}")
    print(f"Probability challenger: {challenger} margin curve. CV gate (beats Elo engine bits): "
          f"{'PASS' if prob_cv else 'FAIL'}\n")

    # ---- 3. Holdout ----
    dev = scored_rows(feats, DEV_FIRST, DEV_LAST)
    hold = scored_rows(feats, HOLDOUT_FIRST, latest)
    holdout, dev_models = {}, {}
    for kind in GRIDS:
        dev_models[kind] = fit(kind, chosen[kind]["params"], feats, dev)
        pred = pd.Series(dev_models[kind].predict(model_inputs(feats[hold], kind)), index=feats.index[hold])
        holdout[kind] = score(pred, win_prob(pred, chosen[kind]["scale"]), feats)
    holdout[ENGINE] = engine_score(feats, feats.index[hold])
    adopt_margin = margin_cv and margin_gate(holdout[candidate], holdout["baseline"])
    adopt_prob = prob_cv and prob_gate(holdout[challenger], holdout[ENGINE])
    margin_verdict = f"ADOPT {candidate}" if adopt_margin else "KEEP ELO BASELINE"
    prob_verdict = f"ADOPT {challenger} margin curve" if adopt_prob else "KEEP ELO ENGINE"
    print(f"Holdout {HOLDOUT_FIRST}-{latest} (look {HOLDOUT_LOOKS}; models trained on {DEV_FIRST}-{DEV_LAST})")
    print(table(holdout))
    print(f"Margin verdict: {margin_verdict}")
    print(f"Probability verdict: {prob_verdict}\n")

    for kind in ("ridge", "xgboost"):
        label = "standardised coefficients" if kind == "ridge" else "gain importance"
        print(f"{kind} {label} (trained {DEV_FIRST}-{DEV_LAST}):")
        for name, value in importances(kind, dev_models[kind], feats):
            print(f"    {name:<30}{value:+10.2f}")
    print()

    # ---- 4. Final refit on all seasons with TUNED_CONFIG features ----
    final_feats = build_features(matches, team_stats, TUNED_CONFIG)
    all_rows = scored_rows(final_feats, DEV_FIRST, latest)
    margin_kind = candidate if adopt_margin else "baseline"
    estimator = fit(margin_kind, chosen[margin_kind]["params"], final_feats, all_rows)
    prob = {}
    if adopt_prob:
        prob_estimator = estimator if challenger == margin_kind else fit(
            challenger, chosen[challenger]["params"], final_feats, all_rows)
        prob = {"prob_source": "margin", "prob_kind": challenger, "prob_estimator": prob_estimator,
                "prob_feature_names": input_names(challenger, final_feats), "scale": chosen[challenger]["scale"]}
    model = TrainedModel(kind=margin_kind, estimator=estimator, feature_names=input_names(margin_kind, final_feats),
                         elo_config_name="TUNED_CONFIG", trained_seasons=(DEV_FIRST, latest),
                         params=chosen[margin_kind]["params"], **prob)
    save(model, MODEL_PATH)
    REPORT_PATH.write_text(json.dumps({
        "run_date": date.today().isoformat(), "holdout_looks": HOLDOUT_LOOKS,
        "holdout_seasons": [HOLDOUT_FIRST, latest],
        "margin_candidate": candidate, "margin_cv_mae_diff": diff, "margin_cv_mae_diff_se": se,
        "margin_cv_passed": margin_cv, "margin_verdict": margin_verdict,
        "prob_challenger": challenger, "prob_cv_passed": prob_cv, "prob_verdict": prob_verdict,
        "final_margin_model": margin_kind, "prob_source": model.prob_source,
        "chosen": chosen, "cv": cv, "holdout": holdout,
    }, indent=2))
    prob_text = "Elo engine probability" if model.prob_source == "elo_engine" else f"{challenger} margin curve"
    print(f"Final model: {margin_kind} margin + {prob_text}, refitted on {DEV_FIRST}-{latest} "
          f"({int(all_rows.sum())} games, TUNED_CONFIG features)")
    print(f"Saved {MODEL_PATH} and {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
