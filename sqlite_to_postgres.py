import os
import sqlite3

# Requires DATABASE_URL to be set in a local .env file for Supabase/Postgres.
from db_postgres import get_postgres_connection, initialize_postgres_db, wrap_connection


def fetch_rows(sqlite_conn, table):
    cursor = sqlite_conn.cursor()
    cursor.execute(f"SELECT * FROM {table}")
    rows = cursor.fetchall()
    columns = [column[0] for column in cursor.description]
    return columns, rows


def migrate_table(pg_conn, table, columns, rows):
    if not rows:
        return 0

    placeholders = ", ".join(["%s"] * len(columns))
    columns_sql = ", ".join(columns)
    insert_sql = (
        f"INSERT INTO {table} ({columns_sql}) VALUES ({placeholders}) "
        "ON CONFLICT DO NOTHING"
    )

    cursor = pg_conn.cursor()
    cursor.executemany(insert_sql, rows)
    return cursor.rowcount


def main():
    sqlite_path = os.getenv("SQLITE_PATH", "leads.db")
    if not os.path.exists(sqlite_path):
        raise FileNotFoundError(f"SQLite database not found: {sqlite_path}")

    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_conn.row_factory = sqlite3.Row

    raw_pg_conn = get_postgres_connection()
    pg_conn = wrap_connection(raw_pg_conn)
    initialize_postgres_db(pg_conn)

    migrated = {}
    for table in ("leads", "subreddits", "templates"):
        columns, rows = fetch_rows(sqlite_conn, table)
        migrated[table] = migrate_table(pg_conn, table, columns, rows)

    pg_conn.commit()
    sqlite_conn.close()
    pg_conn.close()

    print("SQLite → Postgres migration complete.")
    for table, count in migrated.items():
        print(f"- {table}: {count} rows inserted")


if __name__ == "__main__":
    main()
