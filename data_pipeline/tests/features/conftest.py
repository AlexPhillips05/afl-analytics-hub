from datetime import date, timedelta

import pytest

from tests.features.helpers import make_match


@pytest.fixture
def season_matches():
    """A, B, C play a short 2024 season, then A v B opens 2025."""
    d = date(2024, 3, 14)
    return [
        make_match(1, d, "Richmond", "Carlton", 15, 5, 10, 10),                       # Rich +25
        make_match(2, d + timedelta(days=7), "Carlton", "Geelong", 12, 12, 12, 2),    # Carl +10
        make_match(3, d + timedelta(days=21), "Geelong", "Richmond", 8, 8, 10, 10),   # Rich +14 (away)
        make_match(4, date(2025, 3, 13), "Richmond", "Carlton", 10, 10, 10, 10),      # draw, new season
    ]
