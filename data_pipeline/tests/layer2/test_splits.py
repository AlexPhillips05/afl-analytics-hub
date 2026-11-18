from layer2.splits import VALIDATION_SEASONS, walk_forward_folds
from tests.layer2.helpers import synthetic_features


def test_folds_are_walk_forward_over_the_validation_seasons():
    f = synthetic_features()

    folds = walk_forward_folds(f)

    assert [season for season, _, _ in folds] == list(VALIDATION_SEASONS)
    assert 2020 not in VALIDATION_SEASONS
    for season, train, val in folds:
        assert f.loc[train, "season"].max() < season          # only earlier seasons (2021's fold skips 2020)
        assert f.loc[train, "season"].min() == 2010
        assert set(f.loc[val, "season"]) == {season}


def test_scoring_exclusions_apply_to_train_and_validation():
    f = synthetic_features()
    folds = walk_forward_folds(f)

    for _, train, val in folds:
        used = f.loc[train.union(val)]
        assert 2020 not in set(used["season"])
        essendon_2016 = (used["season"] == 2016) & ((used["home_team"] == "Essendon") | (used["away_team"] == "Essendon"))
        assert not essendon_2016.any()
