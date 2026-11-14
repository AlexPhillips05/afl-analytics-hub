import pytest

from elo.config import EloConfig
from elo.vai import VenueAdjustment


@pytest.fixture
def vai():
    return VenueAdjustment(EloConfig())


@pytest.mark.parametrize("home, away, venue, home_vai, away_vai", [
    ("West Coast", "Collingwood", "Perth Stadium", 65.0, 0.0),   # interstate trip
    ("Richmond", "Collingwood", "M.C.G.", 65.0, 45.0),           # same state: label bonus is the gap
    ("Collingwood", "Carlton", "Adelaide Oval", 20.0, 0.0),      # Gather Round: neutral state
    ("Hawthorn", "Sydney", "York Park", 20.0, 0.0),              # Tasmania: no home-state bonus
])
def test_base_values_for_worked_examples(vai, home, away, venue, home_vai, away_vai):
    assert vai.value(home, venue, is_home=True) == pytest.approx(home_vai)
    assert vai.value(away, venue, is_home=False) == pytest.approx(away_vai)


def test_update_is_equal_and_opposite_at_that_venue_only(vai):
    vai.update("West Coast", "Collingwood", "Perth Stadium", rating_change=30.0)

    assert vai.tweaks[("West Coast", "Perth Stadium")] == pytest.approx(3.0)
    assert vai.tweaks[("Collingwood", "Perth Stadium")] == pytest.approx(-3.0)
    assert vai.value("West Coast", "Perth Stadium", is_home=True) == pytest.approx(68.0)
    # Same teams elsewhere are unaffected.
    assert vai.value("West Coast", "Subiaco", is_home=True) == pytest.approx(65.0)
    assert vai.value("Collingwood", "M.C.G.", is_home=True) == pytest.approx(65.0)


def test_updates_accumulate_per_pair(vai):
    vai.update("Geelong", "Hawthorn", "Kardinia Park", rating_change=20.0)
    vai.update("Geelong", "Sydney", "Kardinia Park", rating_change=-10.0)

    assert vai.tweaks[("Geelong", "Kardinia Park")] == pytest.approx(1.0)
    assert vai.tweaks[("Hawthorn", "Kardinia Park")] == pytest.approx(-2.0)
    assert vai.tweaks[("Sydney", "Kardinia Park")] == pytest.approx(1.0)


def test_start_new_season_regresses_tweaks(vai):
    vai.update("West Coast", "Collingwood", "Perth Stadium", rating_change=30.0)

    vai.start_new_season()

    assert vai.tweaks[("West Coast", "Perth Stadium")] == pytest.approx(2.7)
    assert vai.tweaks[("Collingwood", "Perth Stadium")] == pytest.approx(-2.7)


def test_zeroed_constants_turn_vai_off():
    off = VenueAdjustment(EloConfig(home_label_bonus=0.0, home_state_bonus=0.0,
                                    vai_learning_rate=0.0, vai_carryover=0.0))
    off.update("West Coast", "Collingwood", "Perth Stadium", rating_change=30.0)

    assert off.value("West Coast", "Perth Stadium", is_home=True) == 0.0
    assert off.value("Collingwood", "Perth Stadium", is_home=False) == 0.0
