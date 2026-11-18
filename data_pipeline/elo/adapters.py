import re

import pandas as pd

from elo.models import MatchResult

# AFL Tables round codes for finals. "WF" (Wildcard, 2026+) is listed with
# Round.Type "Regular" by AFL Tables, but this project treats it as a final.
FINALS_CODES = frozenset({"WF", "QF", "EF", "SF", "PF", "GF"})

# From 2024 AFL Tables numbers Opening Round as "R1"; this project uses round 0
# for Opening Round, so home-and-away rounds are shifted down by one.
OPENING_ROUND_FIRST_SEASON = 2024

_HOME_AWAY_ROUND = re.compile(r"R(\d+)")


def _home_away_round_number(round_code: str, season: int) -> int | None:
    match = _HOME_AWAY_ROUND.fullmatch(round_code)
    if match is None:
        return None
    number = int(match.group(1))
    return number - 1 if season >= OPENING_ROUND_FIRST_SEASON else number


def afltables_to_matches(df: pd.DataFrame) -> list[MatchResult]:
    """Convert raw fitzRoy::fetch_results_afltables() rows into MatchResults.

    Pure: no I/O. Output is sorted chronologically by (Date, Game), because
    EloEngine trusts input order and rejects dates that go backwards.
    """
    records = (
        df.assign(Date=pd.to_datetime(df["Date"]).dt.date)
        .sort_values(["Date", "Game"], kind="stable")
        .to_dict("records")
    )

    # First pass: validate round codes and find each season's last home-and-away
    # round, which finals use as their (K-irrelevant) round_number.
    last_home_away_round: dict[int, int] = {}
    for row in records:
        season = int(row["Season"])
        code = str(row["Round"])
        number = _home_away_round_number(code, season)
        if number is None:
            if code not in FINALS_CODES:
                raise ValueError(f"Unrecognised AFL Tables round code {code!r} in season {season}")
            continue
        last_home_away_round[season] = max(number, last_home_away_round.get(season, number))

    matches = []
    for row in records:
        season = int(row["Season"])
        code = str(row["Round"])
        is_final = code in FINALS_CODES
        if is_final:
            round_number = last_home_away_round.get(season, 0) + 1
        else:
            round_number = _home_away_round_number(code, season)
        matches.append(MatchResult(
            season=season,
            round_number=round_number,
            is_final=is_final,
            home_team=str(row["Home.Team"]),
            away_team=str(row["Away.Team"]),
            home_goals=int(row["Home.Goals"]),
            home_behinds=int(row["Home.Behinds"]),
            away_goals=int(row["Away.Goals"]),
            away_behinds=int(row["Away.Behinds"]),
            match_id=f"afltables-{int(row['Game'])}",
            date=row["Date"],
            venue=str(row["Venue"]),
            round_code=code,
        ))
    return matches
