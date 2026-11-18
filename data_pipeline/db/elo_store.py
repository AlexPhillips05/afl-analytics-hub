import dataclasses
import json

import pandas as pd
from psycopg2.extras import execute_values

from elo.config import EloConfig

# EloEngine output columns stored per match (same names as the elo_ratings table columns).
RATING_COLUMNS = (
    "home_rating_pre", "away_rating_pre", "home_vai", "away_vai", "expected_home_win_prob",
    "league_avg_conversion", "adjusted_margin", "actual_home_outcome", "rating_change",
    "home_rating_post", "away_rating_post",
)


def config_json(config: EloConfig) -> str:
    return json.dumps(dataclasses.asdict(config))


def rating_rows(run_id: int, history: pd.DataFrame) -> list[tuple]:
    """(run_id, match_id, *RATING_COLUMNS) per engine output row. Pure."""
    values = history[["match_id", *RATING_COLUMNS]].itertuples(index=False, name=None)
    return [(run_id, match_id, *(float(v) for v in rest)) for match_id, *rest in values]


def save_elo_run(conn, name: str, config: EloConfig, history: pd.DataFrame) -> int:
    """Create or update the named run and replace its ratings, in one transaction. Returns the run id."""
    with conn, conn.cursor() as cur:
        cur.execute(
            """INSERT INTO elo_runs (name, config) VALUES (%s, %s::jsonb)
               ON CONFLICT (name) DO UPDATE SET config = EXCLUDED.config, created_at = now()
               RETURNING id""",
            (name, config_json(config)),
        )
        run_id = cur.fetchone()[0]
        cur.execute("DELETE FROM elo_ratings WHERE run_id = %s", (run_id,))
        execute_values(
            cur,
            f"INSERT INTO elo_ratings (run_id, match_id, {', '.join(RATING_COLUMNS)}) VALUES %s",
            rating_rows(run_id, history),
        )
    return run_id
