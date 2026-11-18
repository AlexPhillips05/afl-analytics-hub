"""Synthetic build_features-shaped frames for Layer 2 tests."""
import numpy as np
import pandas as pd


def synthetic_features(seasons=range(2010, 2023), games_per_season=60, seed=0) -> pd.DataFrame:
    """Margin = 0.3*elo_diff + 8*form_margin_diff + noise, so a non-Elo feature carries real signal."""
    rng = np.random.default_rng(seed)
    rows = []
    for season in seasons:
        for g in range(games_per_season):
            elo_diff = rng.normal(0, 60)
            form = rng.normal(0, 1)
            margin = round(0.3 * elo_diff + 8 * form + rng.normal(0, 25))
            rows.append({
                "match_id": f"m{season}-{g}", "season": season, "round_number": 1 + g // 9,
                "date": pd.Timestamp(season, 4, 1) + pd.Timedelta(days=g), "home_team": "Sydney",
                "away_team": "Essendon" if g == 0 else "Geelong", "is_final": False,
                "elo_diff": elo_diff, "vai_diff": rng.normal(0, 20), "elo_home_win_prob": 0.5,
                "rest_diff": np.nan if g < 2 else rng.integers(-3, 4), "home_off_bye": bool(g % 7 == 0),
                "form_margin_diff": np.nan if g < 2 else form,
                "target_home_margin": margin,
                "target_home_result": 1.0 if margin > 0 else 0.5 if margin == 0 else 0.0,
            })
    return pd.DataFrame(rows)
