import os
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv


class PostgresCursorWrapper:
    def __init__(self, cursor):
        self._cursor = cursor

    def execute(self, query, params=None):
        if isinstance(query, bytes):
            query = query.decode()
        converted = query.replace("?", "%s")
        if params is None:
            return self._cursor.execute(converted)
        return self._cursor.execute(converted, params)

    def executemany(self, query, param_list):
        converted = query.replace("?", "%s")
        return self._cursor.executemany(converted, param_list)

    def fetchone(self):
        return self._cursor.fetchone()

    def fetchall(self):
        return self._cursor.fetchall()

    def close(self):
        return self._cursor.close()

    def __getattr__(self, name):
        return getattr(self._cursor, name)


class PostgresConnectionWrapper:
    def __init__(self, connection):
        self._connection = connection

    def cursor(self):
        from psycopg2.extras import RealDictCursor

        return PostgresCursorWrapper(
            self._connection.cursor(cursor_factory=RealDictCursor)
        )

    def commit(self):
        return self._connection.commit()

    def close(self):
        return self._connection.close()

    def __getattr__(self, name):
        return getattr(self._connection, name)


SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


def get_postgres_connection():
    """Create a raw psycopg2 connection using DATABASE_URL."""
    load_dotenv(SCHEMA_PATH.parent / ".env")
    load_dotenv()
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError(
            "DATABASE_URL is not set. Add it to your .env file "
            f"({SCHEMA_PATH.parent / '.env'})."
        )
    import psycopg2

    last_error = None
    for attempt in range(5):
        try:
            return psycopg2.connect(database_url)
        except psycopg2.OperationalError as exc:
            message = str(exc)
            last_error = exc
            if "MaxClientsInSessionMode" in message:
                wait_s = min(1 + attempt, 5)
                print(
                    "⚠️ Postgres connection pool is full. Retrying in "
                    f"{wait_s}s..."
                )
                time.sleep(wait_s)
                continue
            raise
    raise last_error


def wrap_connection(connection):
    return PostgresConnectionWrapper(connection)


def initialize_postgres_db(connection):
    """Create Postgres tables that mirror the existing SQLite schema."""
    cursor = connection.cursor()

    schema_sql = SCHEMA_PATH.read_text()
    statements = [stmt.strip() for stmt in schema_sql.split(";") if stmt.strip()]
    for statement in statements:
        cursor.execute(statement)

    connection.commit()

    ensure_lead_comment_columns(cursor)
    connection.commit()

    cursor.execute("SELECT COUNT(*) AS count FROM subreddits")
    if cursor.fetchone()["count"] == 0:
        default_subs = [
            ("webdev", "high_priority"),
            ("saas", "medium_priority"),
            ("indiehackers", "high_priority"),
            ("startups", "medium_priority"),
        ]
        for name, priority in default_subs:
            cursor.execute(
                """
                INSERT INTO subreddits (name, priority, added_date)
                VALUES (%s, %s, %s)
                ON CONFLICT DO NOTHING
                """,
                (name, priority, datetime.now().isoformat()),
            )

    default_templates = [
        (
            "downtime_issue",
            "Hey! I use StatusMonkey.co for this - it checks every 60 seconds and sends SMS alerts instantly. Only $5.99/mo (free during beta). Has saved me multiple times!",
        ),
        (
            "competitor_complaint",
            "If you think [COMPETITOR] is expensive, check out StatusMonkey. $5.99/mo with 60-second checks, SMS alerts, AND a status page included. Currently free during beta.",
        ),
        (
            "recommendation",
            "I have been using StatusMonkey and it is solid. 60-second monitoring, instant SMS/email alerts, and you get a status page. Best part? Only $5.99/mo and free during beta.",
        ),
    ]
    for name, content in default_templates:
        cursor.execute(
            """
            INSERT INTO templates (name, content)
            VALUES (%s, %s)
            ON CONFLICT DO NOTHING
            """,
            (name, content),
        )

    connection.commit()


def ensure_lead_comment_columns(cursor):
    """Add comment columns if missing, without blocking startup on timeouts."""
    existing = get_leads_comment_columns(cursor)
    missing = {"comment_url", "comment_snippet"} - existing
    if not missing:
        return

    try:
        cursor.execute("SET LOCAL statement_timeout = '5s'")
        if "comment_url" in missing:
            cursor.execute("ALTER TABLE leads ADD COLUMN comment_url TEXT")
        if "comment_snippet" in missing:
            cursor.execute("ALTER TABLE leads ADD COLUMN comment_snippet TEXT")
    except Exception as exc:
        try:
            import psycopg2

            if isinstance(exc, psycopg2.errors.QueryCanceled):
                print("⚠️ Skipping comment column migration due to timeout.")
                return
        except Exception:
            pass
        raise


def get_leads_comment_columns(cursor):
    cursor.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'leads'
          AND column_name IN ('comment_url', 'comment_snippet')
        """
    )
    return {row["column_name"] for row in cursor.fetchall()}
