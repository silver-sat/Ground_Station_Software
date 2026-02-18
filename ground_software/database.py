"""
 @author Lee A. Congdon (lee@silversat.org)
 @author Benjamin S. Cohen (ben@silversat.org)
 @brief initializes and migrates the database

 This program initializes and migrates the database
"""

import sqlite3
import click
from flask import current_app, g


def get_database():
    if "database" not in g:
        g.database = sqlite3.connect(
            current_app.config["DATABASE"], detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.database.row_factory = sqlite3.Row
    return g.database


def close_database(e=None):
    database = g.pop("database", None)
    if database is not None:
        database.close()


def init_database():
    database = get_database()
    with current_app.open_resource("schema.sql") as schema:
        database.executescript(schema.read().decode("utf8"))


def _column_exists(database, table_name, column_name):
    columns = database.execute(f"PRAGMA table_info({table_name})").fetchall()
    return any(column["name"] == column_name for column in columns)


def _ensure_base_tables(database):
    database.execute(
        "CREATE TABLE IF NOT EXISTS transmissions("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP, "
        "message_sequence INTEGER, "
        "command NOT NULL, "
        "status NOT NULL DEFAULT 'pending'"
        ")"
    )
    database.execute(
        "CREATE TABLE IF NOT EXISTS responses("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP, "
        "message_sequence INTEGER, "
        "response NOT NULL"
        ")"
    )
    database.execute(
        "CREATE TABLE IF NOT EXISTS settings("
        "key TEXT PRIMARY KEY, "
        "value DEFAULT CURRENT_TIMESTAMP"
        ")"
    )


def _ensure_message_sequence_columns(database):
    if not _column_exists(database, "transmissions", "message_sequence"):
        database.execute("ALTER TABLE transmissions ADD COLUMN message_sequence INTEGER")
    if not _column_exists(database, "responses", "message_sequence"):
        database.execute("ALTER TABLE responses ADD COLUMN message_sequence INTEGER")


def _backfill_message_sequence(database):
    database.execute("DROP TABLE IF EXISTS _message_order")
    database.execute(
        "CREATE TEMP TABLE _message_order(source TEXT, row_id INTEGER, seq INTEGER)"
    )

    max_tx_row = database.execute(
        "SELECT COALESCE(MAX(message_sequence), 0) AS max_seq FROM transmissions"
    ).fetchone()
    max_rsp_row = database.execute(
        "SELECT COALESCE(MAX(message_sequence), 0) AS max_seq FROM responses"
    ).fetchone()
    max_existing_sequence = max(max_tx_row["max_seq"], max_rsp_row["max_seq"])

    database.execute(
        "INSERT INTO _message_order(source, row_id, seq) "
        "SELECT source, row_id, ? + ROW_NUMBER() OVER (ORDER BY timestamp, row_id, source) "
        "FROM ("
        "  SELECT 't' AS source, id AS row_id, timestamp FROM transmissions WHERE message_sequence IS NULL "
        "  UNION ALL "
        "  SELECT 'r' AS source, id AS row_id, timestamp FROM responses WHERE message_sequence IS NULL"
        ")",
        (max_existing_sequence,),
    )

    database.execute(
        "UPDATE transmissions SET message_sequence = ("
        "SELECT seq FROM _message_order WHERE source='t' AND row_id = transmissions.id"
        ") WHERE message_sequence IS NULL"
    )
    database.execute(
        "UPDATE responses SET message_sequence = ("
        "SELECT seq FROM _message_order WHERE source='r' AND row_id = responses.id"
        ") WHERE message_sequence IS NULL"
    )

    database.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_transmissions_message_sequence "
        "ON transmissions(message_sequence)"
    )
    database.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_responses_message_sequence "
        "ON responses(message_sequence)"
    )


def _migrate_cleared_responses_setting(database):
    cleared_sequence_row = database.execute(
        "SELECT value FROM settings WHERE key = ?", ("responses_cleared_sequence",)
    ).fetchone()
    if cleared_sequence_row is not None:
        return

    cleared_timestamp_row = database.execute(
        "SELECT value FROM settings WHERE key = ?", ("responses_cleared_at",)
    ).fetchone()
    if not cleared_timestamp_row or not cleared_timestamp_row["value"]:
        return

    max_sequence_row = database.execute(
        "SELECT COALESCE(MAX(message_sequence), 0) AS max_sequence "
        "FROM responses WHERE timestamp <= ?",
        (cleared_timestamp_row["value"],),
    ).fetchone()
    database.execute(
        "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
        ("responses_cleared_sequence", str(max_sequence_row["max_sequence"])),
    )


def _update_message_sequence_setting(database):
    max_tx_row = database.execute(
        "SELECT COALESCE(MAX(message_sequence), 0) AS max_seq FROM transmissions"
    ).fetchone()
    max_rsp_row = database.execute(
        "SELECT COALESCE(MAX(message_sequence), 0) AS max_seq FROM responses"
    ).fetchone()
    next_sequence = max(max_tx_row["max_seq"], max_rsp_row["max_seq"], 0) + 1
    database.execute(
        "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
        ("message_sequence", str(next_sequence)),
    )


def _refresh_views(database):
    database.executescript(
        "DROP VIEW IF EXISTS filtered_transmissions;"
        "CREATE VIEW filtered_transmissions AS "
        "SELECT id, timestamp, message_sequence, "
        "substr(command, 3, length(command) - 3) AS command "
        "FROM transmissions WHERE substr(command, 2, 1) <> x'0D';"
        "DROP VIEW IF EXISTS filtered_responses;"
        "CREATE VIEW filtered_responses AS "
        "SELECT id, timestamp, message_sequence, "
        "substr(response, 3, length(response) - 3) AS response "
        "FROM responses "
        "WHERE CAST(SUBSTR(response, 3, 5) AS TEXT) NOT IN ('ACK D', 'RES D');"
        "DROP VIEW IF EXISTS combined_messages;"
        "CREATE VIEW combined_messages AS "
        "SELECT message_sequence, timestamp, 'transmission' AS type, "
        "CAST(SUBSTR(command, 3, LENGTH(command) - 3) AS TEXT) AS message "
        "FROM transmissions WHERE SUBSTR(command, 2, 1) <> x'0D' "
        "UNION ALL "
        "SELECT message_sequence, timestamp, 'response' AS type, "
        "CAST(SUBSTR(response, 3, LENGTH(response) - 3) AS TEXT) AS message "
        "FROM responses "
        "WHERE CAST(SUBSTR(response, 3, 5) AS TEXT) NOT IN ('ACK D', 'RES D') "
        "ORDER BY message_sequence;"
    )


def migrate_database():
    database = get_database()
    _ensure_base_tables(database)
    _ensure_message_sequence_columns(database)
    _backfill_message_sequence(database)
    _migrate_cleared_responses_setting(database)
    _update_message_sequence_setting(database)
    _refresh_views(database)
    database.execute(
        "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
        ("schema_version", "2"),
    )
    database.commit()


def next_sequence_value(database, key, initial_value=1):
    cursor = database.cursor()
    try:
        cursor.execute("BEGIN IMMEDIATE")
        row = cursor.execute(
            "SELECT value FROM settings WHERE key = ?", (key,)
        ).fetchone()

        current_value = initial_value
        if row is not None:
            value = row[0] if not isinstance(row, sqlite3.Row) else row["value"]
            if value is not None:
                try:
                    current_value = int(value)
                except (TypeError, ValueError):
                    current_value = initial_value

        cursor.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, str(current_value + 1)),
        )
        database.commit()
        return current_value
    except Exception:
        database.rollback()
        raise


@click.command("init-database")
def init_database_command():
    init_database()
    click.echo("initialized the database")


@click.command("migrate-database")
def migrate_database_command():
    migrate_database()
    click.echo("migrated the database")


def init_app(application):
    application.teardown_appcontext(close_database)
    application.cli.add_command(init_database_command)
    application.cli.add_command(migrate_database_command)

    with application.app_context():
        migrate_database()
