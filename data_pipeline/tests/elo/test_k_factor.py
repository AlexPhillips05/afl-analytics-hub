import pytest

from elo.config import EloConfig
from elo.k_factor import k_factor


@pytest.fixture
def config():
    return EloConfig()


def test_round_zero_is_k_early(config):
    assert k_factor(0, is_final=False, config=config) == pytest.approx(38.0)


def test_round_seven_decays_toward_k_late(config):
    assert k_factor(7, is_final=False, config=config) == pytest.approx(27.886071058743077)


def test_round_twenty_one_is_near_k_late(config):
    assert k_factor(21, is_final=False, config=config) == pytest.approx(22.79659309388582)


def test_finals_use_fixed_k_regardless_of_round(config):
    assert k_factor(1, is_final=True, config=config) == pytest.approx(34.0)
    assert k_factor(24, is_final=True, config=config) == pytest.approx(34.0)
