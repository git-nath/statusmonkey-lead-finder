import os
import sqlite3

from db_postgres import (
    get_postgres_connection,
    initialize_postgres_db,
    wrap_connection,
)


def is_postgres_enabled():
    return os.getenv("USE_POSTGRES", "false").lower() in {"1", "true", "yes", "on"}


def get_db_connection():
    if is_postgres_enabled():
        return wrap_connection(get_postgres_connection())

    conn = sqlite3.connect("leads.db")
    conn.row_factory = sqlite3.Row
    return conn


def dict_from_row(row):
    if row is None:
        return None
    if isinstance(row, sqlite3.Row):
        return dict(zip(row.keys(), row))
    if isinstance(row, dict):
        return row
    return dict(row)


try:
    from psycopg2 import IntegrityError as PostgresIntegrityError

    DBIntegrityError = (sqlite3.IntegrityError, PostgresIntegrityError)
except ImportError:  # psycopg2 may not be installed until Postgres is enabled
    DBIntegrityError = sqlite3.IntegrityError


def initialize_database():
    if is_postgres_enabled():
        conn = get_db_connection()
        initialize_postgres_db(conn)
        conn.close()
        print("Postgres database initialized successfully!")
