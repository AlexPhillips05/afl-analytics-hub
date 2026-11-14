import pytest

from elo.config import EloConfig
from elo.mov import mov_multiplier


@pytest.fixture
def config():
    return EloConfig()


MARGIN = 44.33333333333334


def test_larger_margin_gives_larger_multiplier_with_diminishing_returns(config):
    small = mov_multiplier(margin=6, elo_diff=0, config=config)
    large = mov_multiplier(margin=60, elo_diff=0, config=config)

    assert small == pytest.approx(1.1931471805599454)  # ln(2) + 0.5
    assert large == pytest.approx(2.8978952727983707)  # ln(11) + 0.5
    assert large > small
    # diminishing returns: a 10x margin increase gives far less than a 10x multiplier increase
    assert large / small < 10


def test_favourite_win_is_dampened_more_as_rating_gap_grows(config):
    no_gap = mov_multiplier(margin=MARGIN, elo_diff=0, config=config)
    medium_gap = mov_multiplier(margin=MARGIN, elo_diff=300, config=config)
    large_gap = mov_multiplier(margin=MARGIN, elo_diff=600, config=config)

    assert no_gap == pytest.approx(2.6269080789187598)
    assert medium_gap == pytest.approx(1.9315500580285)
    assert large_gap == pytest.approx(1.5272721389062558)
    assert no_gap > medium_gap > large_gap


def test_upset_is_not_dampened(config):
    # Home was the 300-point underdog and won by the same margin: no dampening.
    upset = mov_multiplier(margin=MARGIN, elo_diff=-300, config=config)
    expected_blowout = mov_multiplier(margin=MARGIN, elo_diff=300, config=config)

    assert upset == pytest.approx(2.6269080789187598)
    assert upset > expected_blowout


def test_dampening_is_from_the_winners_perspective(config):
    # Away team was the 300-point favourite and won: same dampening as a home favourite win.
    away_favourite_win = mov_multiplier(margin=-MARGIN, elo_diff=-300, config=config)
    home_favourite_win = mov_multiplier(margin=MARGIN, elo_diff=300, config=config)

    assert away_favourite_win == pytest.approx(home_favourite_win)


def test_draw_gives_floor_multiplier_not_zero(config):
    assert mov_multiplier(margin=0, elo_diff=250, config=config) == pytest.approx(0.5)
