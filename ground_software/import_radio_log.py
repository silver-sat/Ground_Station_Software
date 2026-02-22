#!/usr/bin/env python3
"""
Import a text radio log file into the radio_logs table for testing/development.

Uses today's date with the embedded HH:MM:SS time found in each log line.
"""

import argparse
import datetime
import os
import re
import sqlite3

from ground_software.database import next_sequence_value


TIME_PATTERN = re.compile(r"(?<!\d)([01]?\d|2[0-3]):([0-5]\d):([0-5]\d)(?:\.\d+)?(?!\d)")


def _extract_hms(log_line):
    match = TIME_PATTERN.search(log_line)
    if not match:
        return None
    hour, minute, second = match.group(1), match.group(2), match.group(3)
    return f"{int(hour):02d}:{minute}:{second}"


def import_radio_log_file(log_file_path, db_path, import_date):
    imported_count = 0
    skipped_count = 0

    connection = sqlite3.connect(db_path)
    connection.isolation_level = None
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA busy_timeout = 5000")
    cursor = connection.cursor()

    try:
        with open(log_file_path, "r", encoding="utf-8", errors="replace") as log_file:
            for raw_line in log_file:
                log_line = raw_line.rstrip("\r\n")
                if not log_line:
                    continue

                time_part = _extract_hms(log_line)
                if not time_part:
                    skipped_count += 1
                    continue

                timestamp = f"{import_date} {time_part}"
                message_sequence = next_sequence_value(connection, "message_sequence", 1)
                cursor.execute(
                    "INSERT INTO radio_logs (timestamp, message_sequence, log_line) VALUES (?, ?, ?)",
                    (timestamp, message_sequence, log_line),
                )
                imported_count += 1
        return imported_count, skipped_count
    finally:
        connection.close()


def main():
    parser = argparse.ArgumentParser(
        description="One-time import of radio log lines into sqlite radio_logs table"
    )
    parser.add_argument("log_file", help="Path to text radio log file to import")
    parser.add_argument(
        "--db",
        default="./instance/radio.db",
        help="Path to sqlite database (default: ./instance/radio.db)",
    )
    parser.add_argument(
        "--log-date",
        "--date",
        dest="log_date",
        default=datetime.date.today().isoformat(),
        help="Date of the log in YYYY-MM-DD format (default: today)",
    )
    args = parser.parse_args()

    try:
        datetime.date.fromisoformat(args.log_date)
    except ValueError as error:
        raise SystemExit(
            f"Invalid --log-date value '{args.log_date}'. Use YYYY-MM-DD."
        ) from error

    db_path = os.path.abspath(args.db)
    imported, skipped = import_radio_log_file(args.log_file, db_path, args.log_date)
    print(f"Imported {imported} radio log lines into {db_path}")
    if skipped:
        print(f"Skipped {skipped} line(s) with no HH:MM:SS timestamp")


if __name__ == "__main__":
    main()
