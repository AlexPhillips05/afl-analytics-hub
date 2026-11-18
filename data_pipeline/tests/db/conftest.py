import pytest

from db.connection import connect, database_url

TABLES = "elo_ratings, elo_runs, matches, raw_afltables_results, teams, venues"


@pytest.fixture
def db_conn():
    """Connection to the TEST database with every table emptied. Skips if TEST_DATABASE_URL isn't set.

    The schema must already be applied: cd database && npm run migrate:deploy:test
    """
    try:
        url = database_url("TEST_DATABASE_URL")
    except RuntimeError:
        pytest.skip("TEST_DATABASE_URL not set")
    conn = connect(url)
    with conn, conn.cursor() as cur:
        cur.execute("SELECT current_database()")
        name = cur.fetchone()[0]
        # Safety net: never truncate anything that isn't a test database.
        assert name.endswith("_test"), f"refusing to truncate non-test database {name!r}"
        cur.execute(f"TRUNCATE {TABLES} RESTART IDENTITY CASCADE")
    yield conn
    conn.close()
