#!/usr/bin/env python3
"""
 @brief Reads text radio log lines from a serial port and stores them in the database
"""

import argparse
import os
import sqlite3
import serial
import time

from ground_software.database import next_sequence_value

BAUD_RATE = 19200
retry_delay = 5  # seconds


def serial_log_read(serial_port, shutdown_event=None):
    while not (shutdown_event and shutdown_event.is_set()):
        try:
            log_serial = serial.Serial(serial_port, BAUD_RATE, timeout=1)
            break
        except Exception:
            print(
                f"Failed to connect to radio log port {serial_port}, retrying in {retry_delay} seconds..."
            )
            time.sleep(retry_delay)
            continue

    if shutdown_event and shutdown_event.is_set():
        return

    db_path = os.path.abspath("./instance/radio.db")
    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA busy_timeout = 5000")

    try:
        while not (shutdown_event and shutdown_event.is_set()):
            try:
                raw_line = log_serial.readline()
            except Exception:
                break

            if not raw_line:
                continue

            log_line = raw_line.decode("utf-8", errors="replace").rstrip("\r\n")
            if not log_line:
                continue

            message_sequence = next_sequence_value(connection, "message_sequence", 1)
            cursor.execute(
                "INSERT INTO radio_logs (message_sequence, log_line) VALUES (?, ?)",
                (message_sequence, log_line),
            )
            connection.commit()
    finally:
        try:
            log_serial.close()
        except Exception:
            pass
        connection.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Serial radio log interface for ground station"
    )
    parser.add_argument(
        "port",
        nargs="?",
        default="/tmp/radio_log",
        help="Serial port path to read text radio logs from (default: /tmp/radio_log)",
    )
    args = parser.parse_args()
    serial_log_read(args.port)
