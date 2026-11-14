import math

import pandas as pd

WARM_UP_LAST_SEASON = 2009  # 2000-2009 only warm up ratings (CLAUDE.md: Historical Data Range)
COVID_SEASON = 2020


def match_bits(p_home: float, home_score: int, away_score: int) -> float:
    """Monash bits: 1 + log2(probability given to the actual result)."""
    if home_score == away_score:
        return 1 + 0.5 * math.log2(p_home * (1 - p_home))
    if home_score > away_score:
        return 1 + math.log2(p_home)
    return 1 + math.log2(1 - p_home)


def tip_correct(p_home: float, home_score: int, away_score: int) -> bool:
    """Tip home when p_home >= 0.5. Draws count as correct (Squiggle convention)."""
    if home_score == away_score:
        return True
    return (p_home >= 0.5) == (home_score > away_score)


def end_of_season_ratings(history: pd.DataFrame) -> pd.DataFrame:
    """Each team's last post-game rating per season. Columns: season, team, rating."""
    home = history[["season", "home_team", "home_rating_post"]].set_axis(["season", "team", "rating"], axis=1)
    away = history[["season", "away_team", "away_rating_post"]].set_axis(["season", "team", "rating"], axis=1)
    # Interleave home/away rows in match order so "last" means the team's last game.
    order = list(range(len(history)))
    long = pd.concat([home.assign(_order=order), away.assign(_order=order)]).sort_values("_order", kind="stable")
    return long.groupby(["season", "team"], as_index=False).last()[["season", "team", "rating"]]


def season_metrics(history: pd.DataFrame) -> pd.DataFrame:
    """One row per season. `history` is EloEngine output plus home_score/away_score, in match order."""
    df = history.assign(
        correct=[tip_correct(p, h, a) for p, h, a in
                 zip(history["expected_home_win_prob"], history["home_score"], history["away_score"])],
        bits=[match_bits(p, h, a) for p, h, a in
              zip(history["expected_home_win_prob"], history["home_score"], history["away_score"])],
        home_baseline=history["home_score"] >= history["away_score"],
        abs_change=history["rating_change"].abs(),
    )
    per_season = df.groupby("season").agg(
        games=("correct", "size"),
        tip_accuracy=("correct", "mean"),
        bits_total=("bits", "sum"),
        bits_per_game=("bits", "mean"),
        home_baseline_accuracy=("home_baseline", "mean"),
        mean_abs_rating_change=("abs_change", "mean"),
    )
    end = end_of_season_ratings(history).groupby("season")["rating"]
    per_season["end_rating_sd"] = end.std()
    per_season["end_rating_range"] = end.max() - end.min()
    per_season["note"] = [
        "warm-up" if s <= WARM_UP_LAST_SEASON else "COVID" if s == COVID_SEASON else ""
        for s in per_season.index
    ]
    return per_season.reset_index()
