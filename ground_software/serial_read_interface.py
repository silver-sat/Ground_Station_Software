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
from ground_software.database import next_sequence_value

BAUD_RATE = 19200
retry_delay = 5  # seconds
FEND = b"\xC0"


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


def serial_read(serial_port, shutdown_event=None):
    """Read from the given serial_port and write responses to the database."""
    while not (shutdown_event and shutdown_event.is_set()):
        try:
            # opening serial connection
            radio_serial = serial.Serial(serial_port, BAUD_RATE, timeout=1)
            break
        except Exception:
            print(f"Failed to connect to serial port {serial_port}, retrying in {retry_delay} seconds...")
            time.sleep(retry_delay)
            continue

    if shutdown_event and shutdown_event.is_set():
        return

    # open database
    db_path = os.path.abspath("./instance/radio.db")
    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA busy_timeout = 5000")

    # read the responses from the radio
    try:
        while not (shutdown_event and shutdown_event.is_set()):
            try:
                response = read_kiss_frame(radio_serial)
            except Exception:
                break
            if response is None:
                continue
            message_sequence = next_sequence_value(connection, "message_sequence", 1)
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
