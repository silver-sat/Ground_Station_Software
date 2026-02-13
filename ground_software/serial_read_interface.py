#!/usr/bin/env python3
"""
 @author Lee A. Congdon (lee@silversat.org)
 @author Benjamin S. Cohen (ben@silversat.org)
 @author Dominik Honzak (dominik@silversat.org)
 @brief SilverSat User and radio Doppler interface
 
 This program provides the radio interface for receiving responses and storing them in the database
 
"""

# imports
import argparse
import os
import sqlite3
import serial
import time
import sys

BAUD_RATE = 19200
retry_delay = 5  # seconds
FEND = b"\xC0"


def next_message_sequence(connection, cursor):
    cursor.execute("BEGIN IMMEDIATE")
    row = cursor.execute(
        "SELECT value FROM settings WHERE key = ?", ("message_sequence",)
    ).fetchone()
    if row and row[0] is not None:
        try:
            current_sequence = int(row[0])
        except (TypeError, ValueError):
            current_sequence = 1
    else:
        current_sequence = 1

    cursor.execute(
        "INSERT INTO settings (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        ("message_sequence", str(current_sequence + 1)),
    )
    connection.commit()
    return current_sequence


def read_kiss_frame(radio_serial):
    while True:
        first = radio_serial.read(1)
        if not first:
            return None
        if first == FEND:
            break

    payload = radio_serial.read_until(expected=FEND)
    if not payload:
        return None
    if payload[-1:] != FEND:
        return None

    return FEND + payload


def serial_read(serial_port):
    """Read from the given serial_port and write responses to the database."""
    while True:
        try:
            # opening serial connection
            radio_serial = serial.Serial(serial_port, BAUD_RATE, timeout=1)
            break
        except Exception:
            print(f"Failed to connect to serial port {serial_port}, retrying in {retry_delay} seconds...")
            time.sleep(retry_delay)
            continue

    # open database
    db_path = os.path.abspath("./instance/radio.db")
    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA busy_timeout = 5000")

    # read the responses from the radio
    try:
        while True:
            try:
                response = read_kiss_frame(radio_serial)
            except Exception:
                break
            if response is None:
                continue
            message_sequence = next_message_sequence(connection, cursor)
            cursor.execute(
                "INSERT INTO responses (message_sequence, response) VALUES (?, ?)",
                (message_sequence, response),
            )
            connection.commit()
    except KeyboardInterrupt:
        print("Interrupted, closing serial connection.")
    finally:
        try:
            radio_serial.close()
        except Exception:
            pass
        connection.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Serial read interface for ground station")
    parser.add_argument(
        "port",
        nargs="?",
        default="/tmp/radio",
        help="Serial port path to read from (default: /tmp/radio)",
    )
    args = parser.parse_args()
    serial_read(args.port)
