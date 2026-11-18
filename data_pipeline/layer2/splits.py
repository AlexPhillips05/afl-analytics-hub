import pandas as pd

from elo.tuning import scored_mask

DEV_FIRST, DEV_LAST = 2010, 2021
# Walk-forward validation seasons inside development (2020 is excluded from scoring entirely).
VALIDATION_SEASONS = (2014, 2015, 2016, 2017, 2018, 2019, 2021)


def scored_rows(features: pd.DataFrame, first: int, last: int) -> pd.Series:
    """Rows used for training/scoring: seasons first..last, minus 2020 and 2016 Essendon games."""
    return scored_mask(features, first, last)


def walk_forward_folds(features: pd.DataFrame, val_seasons=VALIDATION_SEASONS) -> list[tuple[int, pd.Index, pd.Index]]:
    """(season, train index, validation index) per fold: train on scored DEV_FIRST..season-1, validate on season."""
    folds = []
    for season in val_seasons:
        train = features.index[scored_rows(features, DEV_FIRST, season - 1)]
        val = features.index[scored_rows(features, season, season)]
        folds.append((season, train, val))
    return folds
