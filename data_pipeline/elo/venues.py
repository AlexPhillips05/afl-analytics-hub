# Home state of each team and venue, used for the Venue Adjustment Index base value.
# Names are AFL Tables' (as produced by fitzRoy::fetch_results_afltables()).
# Unknown names raise, so a new ground or team must be added here deliberately
# rather than silently getting no home-state advantage.

TEAM_STATE: dict[str, str] = {
    "Carlton": "VIC", "Collingwood": "VIC", "Essendon": "VIC", "Footscray": "VIC",
    "Geelong": "VIC", "Hawthorn": "VIC", "Melbourne": "VIC", "North Melbourne": "VIC",
    "Richmond": "VIC", "St Kilda": "VIC",
    "West Coast": "WA", "Fremantle": "WA",
    "Adelaide": "SA", "Port Adelaide": "SA",
    "Brisbane Lions": "QLD", "Gold Coast": "QLD",
    "Sydney": "NSW", "GWS": "NSW",
}

VENUE_STATE: dict[str, str] = {
    # VIC
    "M.C.G.": "VIC", "Docklands": "VIC", "Kardinia Park": "VIC", "Princes Park": "VIC",
    "Eureka Stadium": "VIC",
    # WA
    "Subiaco": "WA", "Perth Stadium": "WA", "W.A.C.A.": "WA", "Hands Oval": "WA",
    # SA
    "Football Park": "SA", "Adelaide Oval": "SA", "Norwood Oval": "SA", "Barossa Park": "SA",
    "Summit Sports Park": "SA",
    # QLD
    "Gabba": "QLD", "Carrara": "QLD", "Cazaly's Stadium": "QLD", "Riverway Stadium": "QLD",
    # NSW
    "S.C.G.": "NSW", "Sydney Showground": "NSW", "Stadium Australia": "NSW", "Blacktown": "NSW",
    # ACT / TAS / NT
    "Manuka Oval": "ACT",
    "York Park": "TAS", "Bellerive Oval": "TAS",
    "Marrara Oval": "NT", "Traeger Park": "NT",
    # Overseas — no team's home state
    "Jiangwan Stadium": "CHN", "Wellington": "NZ",
}


def team_state(team: str) -> str:
    try:
        return TEAM_STATE[team]
    except KeyError:
        raise ValueError(f"Unknown team {team!r}: add it to TEAM_STATE in elo/venues.py") from None


def venue_state(venue: str) -> str:
    try:
        return VENUE_STATE[venue]
    except KeyError:
        raise ValueError(f"Unknown venue {venue!r}: add it to VENUE_STATE in elo/venues.py") from None
