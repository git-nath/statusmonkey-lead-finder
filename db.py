from psycopg2 import IntegrityError as PostgresIntegrityError

from db_postgres import get_postgres_connection, initialize_postgres_db, wrap_connection

try:
    from flask import g, has_app_context
except Exception:
    g = None
    has_app_context = None

DBIntegrityError = PostgresIntegrityError


def get_db_connection():
    """Create a Postgres connection, reusing one per request when possible."""
    if has_app_context and has_app_context():
        if g is not None:
            conn = g.get("db_conn")
            if conn is None or getattr(conn, "closed", False):
                conn = wrap_connection(get_postgres_connection())
                g.db_conn = conn
            return conn
    return wrap_connection(get_postgres_connection())


def close_db_connection(exception=None):
    if g is None:
        return
    conn = g.pop("db_conn", None)
    if conn is not None and not getattr(conn, "closed", False):
        conn.close()


def dict_from_row(row):
    if row is None:
        return None
    if isinstance(row, dict):
        return row
    return dict(row)


def initialize_database():
    conn = wrap_connection(get_postgres_connection())
    initialize_postgres_db(conn)
    conn.close()
    print("Postgres database initialized successfully!")
