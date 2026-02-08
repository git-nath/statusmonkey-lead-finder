import os
import sqlite3
from pathlib import Path

# Requires DATABASE_URL to be set in a local .env file for Supabase/Postgres.
from dotenv import load_dotenv

from db_postgres import get_postgres_connection, wrap_connection


TYPE_MAP = {
    "INTEGER": "INTEGER",
    "INT": "INTEGER",
    "REAL": "DOUBLE PRECISION",
    "TEXT": "TEXT",
    "BLOB": "BYTEA",
    "NUMERIC": "NUMERIC",
}


def normalize_type(type_name):
    if not type_name:
        return "TEXT"
    upper = type_name.upper()
    for key, mapped in TYPE_MAP.items():
        if key in upper:
            return mapped
    return "TEXT"


def get_sqlite_tables(sqlite_conn):
    cursor = sqlite_conn.cursor()
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name != 'sqlite_sequence'"
    )
    return [row[0] for row in cursor.fetchall()]


def get_table_columns(sqlite_conn, table_name):
    cursor = sqlite_conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = []
    primary_keys = []
    for col in cursor.fetchall():
        columns.append(
            {
                "name": col[1],
                "type": normalize_type(col[2]),
                "notnull": bool(col[3]),
                "default": col[4],
                "pk": bool(col[5]),
            }
        )
        if col[5]:
            primary_keys.append(col[1])
    return columns, primary_keys


def create_postgres_table(pg_conn, table_name, columns, primary_keys):
    column_defs = []
    for col in columns:
        line = f"{col['name']} {col['type']}"
        if col["notnull"]:
            line += " NOT NULL"
        if col["default"] is not None:
            line += f" DEFAULT {col['default']}"
        column_defs.append(line)

    if primary_keys:
        column_defs.append(f"PRIMARY KEY ({', '.join(primary_keys)})")

    create_sql = f"CREATE TABLE IF NOT EXISTS {table_name} ({', '.join(column_defs)})"
    cursor = pg_conn.cursor()
    cursor.execute(create_sql)


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
    load_dotenv(Path(__file__).resolve().parent / ".env")
    print(f"Using DATABASE_URL: {os.getenv('DATABASE_URL')}")
    sqlite_path = os.getenv("SQLITE_PATH", "leads.db")
    if not os.path.exists(sqlite_path):
        raise FileNotFoundError(f"SQLite database not found: {sqlite_path}")

    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_conn.row_factory = sqlite3.Row

    raw_pg_conn = get_postgres_connection()
    pg_conn = wrap_connection(raw_pg_conn)

    migrated = {}
    tables = get_sqlite_tables(sqlite_conn)
    for table in tables:
        columns, primary_keys = get_table_columns(sqlite_conn, table)
        create_postgres_table(pg_conn, table, columns, primary_keys)
        column_names, rows = fetch_rows(sqlite_conn, table)
        migrated[table] = migrate_table(pg_conn, table, column_names, rows)

    pg_conn.commit()
    sqlite_conn.close()
    pg_conn.close()

    print("SQLite → Postgres migration complete.")
    for table, count in migrated.items():
        print(f"- {table}: {count} rows inserted")


if __name__ == "__main__":
    main()
