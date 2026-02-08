from psycopg2 import IntegrityError as PostgresIntegrityError

from db_postgres import get_postgres_connection, initialize_postgres_db, wrap_connection

DBIntegrityError = PostgresIntegrityError


def get_db_connection():
    """Create a short-lived Postgres connection for each request."""
    return wrap_connection(get_postgres_connection())


def dict_from_row(row):
    if row is None:
        return None
    if isinstance(row, dict):
        return row
    return dict(row)


def initialize_database():
    conn = get_db_connection()
    initialize_postgres_db(conn)
    conn.close()
    print("Postgres database initialized successfully!")
