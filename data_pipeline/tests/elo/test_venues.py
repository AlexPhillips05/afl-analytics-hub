import pytest

from elo.venues import TEAM_STATE, VENUE_STATE, team_state, venue_state

# Every venue in the AFL Tables 2000-2026 results (checked 2026-11-14).
ALL_VENUES_2000_2026 = [
    "M.C.G.", "Docklands", "Subiaco", "Gabba", "Football Park", "Adelaide Oval", "S.C.G.",
    "Kardinia Park", "Perth Stadium", "Carrara", "Sydney Showground", "York Park", "Manuka Oval",
    "Stadium Australia", "Princes Park", "Bellerive Oval", "Marrara Oval", "Eureka Stadium",
    "Cazaly's Stadium", "Traeger Park", "Norwood Oval", "W.A.C.A.", "Barossa Park",
    "Jiangwan Stadium", "Summit Sports Park", "Wellington", "Hands Oval", "Blacktown",
    "Riverway Stadium",
]


def test_known_venues_map_to_their_state():
    assert venue_state("Perth Stadium") == "WA"
    assert venue_state("M.C.G.") == "VIC"
    assert venue_state("York Park") == "TAS"
    assert venue_state("Manuka Oval") == "ACT"
    assert venue_state("Jiangwan Stadium") == "CHN"


def test_known_teams_map_to_their_state():
    assert team_state("GWS") == "NSW"
    assert team_state("Footscray") == "VIC"
    assert team_state("Brisbane Lions") == "QLD"
    assert len(TEAM_STATE) == 18


def test_every_venue_in_the_historical_data_is_mapped():
    assert len(ALL_VENUES_2000_2026) == 29
    assert set(ALL_VENUES_2000_2026) <= set(VENUE_STATE)


def test_unknown_names_raise():
    with pytest.raises(ValueError, match="Nowhere Oval"):
        venue_state("Nowhere Oval")
    with pytest.raises(ValueError, match="Tasmania"):
        team_state("Tasmania")
