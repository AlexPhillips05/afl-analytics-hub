from psycopg2.extras import execute_values

from elo.venues import TEAM_STATE, VENUE_STATE


def _sync(cur, table: str, states: dict[str, str]) -> dict[str, int]:
    # `table` is one of two fixed names below, never user input.
    execute_values(
        cur,
        f"INSERT INTO {table} (name, state) VALUES %s ON CONFLICT (name) DO UPDATE SET state = EXCLUDED.state",
        sorted(states.items()),
    )
    cur.execute(f"SELECT name, id FROM {table}")
    return dict(cur.fetchall())


def sync_reference_data(conn) -> tuple[dict[str, int], dict[str, int]]:
    """Upsert teams and venues from elo/venues.py (the source of truth). Returns name -> id maps."""
    with conn, conn.cursor() as cur:
        team_ids = _sync(cur, "teams", TEAM_STATE)
        venue_ids = _sync(cur, "venues", VENUE_STATE)
    return team_ids, venue_ids
