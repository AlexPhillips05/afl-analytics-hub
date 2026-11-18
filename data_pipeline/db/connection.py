import os
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

# One gitignored file holds the connection URLs for Python, R and Prisma (see .env.example).
ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


def database_url(env_var: str = "DATABASE_URL") -> str:
    """Return a connection URL. An already-set environment variable wins over the .env file."""
    load_dotenv(ENV_FILE)  # does not override variables that are already set
    url = os.environ.get(env_var)
    if not url:
        raise RuntimeError(f"{env_var} is not set: add it to {ENV_FILE} (see .env.example)")
    return url


def connect(url: str | None = None):
    return psycopg2.connect(url or database_url())
