"""Sum raw AFL Tables player rows (raw_afltables_player_stats) into team_match_stats.

Every match must get exactly its two teams' stats, or nothing is written. Replacing matches
(load_matches.py) clears team_match_stats (cascade), so run this after load_matches.py.

Usage (from the repo root, data_pipeline venv active; after fetch_player_stats.R and load_matches.py):
    python data_pipeline/load_team_stats.py
"""
import sys
from contextlib import closing

from db.connection import connect
from db.matches import read_matches
from db.reference import sync_reference_data
from db.team_stats import aggregate_team_stats, read_raw_player_stats, replace_team_stats


def main() -> int:
    with closing(connect()) as conn:  # db functions manage their own transactions
        matches = read_matches(conn)
        players = read_raw_player_stats(conn)
        if not matches or players.empty:
            print("Need matches and raw player stats: run fetch_results.R, fetch_player_stats.R, load_matches.py.",
                  file=sys.stderr)
            return 1
        team_ids, _ = sync_reference_data(conn)
        team_stats = aggregate_team_stats(players, matches)
        written = replace_team_stats(conn, team_stats, team_ids)
    print(f"Summed {len(players)} player rows into {written} team-match rows ({len(matches)} matches)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
