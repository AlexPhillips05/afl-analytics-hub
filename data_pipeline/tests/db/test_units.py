import dataclasses
import json
from datetime import date

import pandas as pd
import pytest

from db.elo_store import RATING_COLUMNS, config_json, rating_rows
from db.matches import RAW_COLUMNS, match_rows
from elo.config import EloConfig
from elo.models import MatchResult
from elo.tuned import TUNED_CONFIG


def _match(**overrides):
    fields = dict(season=2025, round_number=1, is_final=False, home_team="Sydney", away_team="GWS",
                  home_goals=12, home_behinds=8, away_goals=10, away_behinds=11,
                  match_id="afltables-17000", date=date(2025, 3, 15), venue="S.C.G.", round_code="R2")
    return MatchResult(**{**fields, **overrides})


def test_raw_columns_cover_every_afltables_column_the_adapter_reads():
    adapter_reads = {"Game", "Date", "Round", "Season", "Home.Team", "Home.Goals", "Home.Behinds",
                     "Away.Team", "Away.Goals", "Away.Behinds", "Venue"}
    assert adapter_reads <= set(RAW_COLUMNS.values())
    assert len(RAW_COLUMNS) == 16


def test_match_rows_looks_up_ids_and_parses_game_number():
    [row] = match_rows([_match()], team_ids={"Sydney": 7, "GWS": 9}, venue_ids={"S.C.G.": 3})

    assert row == ("afltables-17000", 17000, 2025, 1, "R2", False, date(2025, 3, 15),
                   3, 7, 9, 12, 8, 10, 11)


def test_match_rows_names_an_unknown_team():
    with pytest.raises(KeyError, match="Tasmania"):
        match_rows([_match(away_team="Tasmania")], team_ids={"Sydney": 7}, venue_ids={"S.C.G.": 3})


def test_config_json_round_trips_every_field():
    assert json.loads(config_json(TUNED_CONFIG)) == dataclasses.asdict(TUNED_CONFIG)
    assert EloConfig(**json.loads(config_json(TUNED_CONFIG))) == TUNED_CONFIG


def test_rating_rows_take_columns_in_table_order():
    history = pd.DataFrame([{"match_id": "afltables-1", "season": 2025, **{c: i + 0.5 for i, c in enumerate(RATING_COLUMNS)}}])

    [row] = rating_rows(4, history)

    assert row == (4, "afltables-1", *(i + 0.5 for i in range(len(RATING_COLUMNS))))
