"""Turn raw AFL Tables rows (raw_afltables_results) into clean matches.

Syncs teams/venues from elo/venues.py, runs the tested AFL Tables adapter (Opening Round, Wildcard,
chronological order) and replaces the matches table. Replacing matches clears elo_ratings (cascade),
so run run_elo_history.py afterwards.

Usage (from the repo root, data_pipeline venv active; after fetch_results.R):
    python data_pipeline/load_matches.py
"""
import sys
from contextlib import closing

from db.connection import connect
from db.matches import read_matches, read_raw_results, replace_matches
from db.reference import sync_reference_data
from elo.adapters import afltables_to_matches


def main() -> int:
    with closing(connect()) as conn:  # db functions manage their own transactions
        team_ids, venue_ids = sync_reference_data(conn)
        raw = read_raw_results(conn)
        if raw.empty:
            print("raw_afltables_results is empty. Run `Rscript data_pipeline/fetch_results.R` first.",
                  file=sys.stderr)
            return 1
        written = replace_matches(conn, afltables_to_matches(raw), team_ids, venue_ids)
        seasons = {m.season for m in read_matches(conn)}
    print(f"Synced {len(team_ids)} teams and {len(venue_ids)} venues")
    print(f"Loaded {written} matches ({min(seasons)}-{max(seasons)}) into matches")
    print("Elo ratings were cleared by the reload: run data_pipeline/run_elo_history.py next")
    return 0


if __name__ == "__main__":
    sys.exit(main())
