#!/usr/bin/env python3
"""
 @author Lee A. Congdon (lee@silversat.org)
 @author Benjamin S. Cohen (ben@silversat.org)
 @author Dominik Honzak (dominik@silversat.org)
 @brief SilverSat User and radio Doppler interface
 
 This program provides the radio interface for sending commands from the database to the satellite
 
"""

# imports
import argparse
import sqlite3
import serial
import time
import logging
import sys

BAUD_RATE = 19200
retry_delay = 5  # seconds


def serial_write(serial_port):
    # open database
    connection = sqlite3.connect("./instance/radio.db")
    cursor = connection.cursor()

    # serial connection
    logging.info("Opening serial port %s @ %d", serial_port, BAUD_RATE)

    while True:
        try:
            # opening serial connection with a short timeout
            radio_serial = serial.Serial(serial_port, BAUD_RATE, timeout=1)
            break
        except Exception as e:
            print(f"Failed to connect to serial port {serial_port}, retrying in {retry_delay} seconds... ({e})")
            time.sleep(retry_delay)
            continue

    try:
        while True:
            try:
                result = cursor.execute(
                    "SELECT * FROM transmissions WHERE status='pending' ORDER BY id ASC LIMIT 1"
                )
                row = result.fetchone()
                if row is None:
                    time.sleep(1)
                    continue

                id, timestamp, command, status = row
                radio_serial.write(command)
                cursor.execute(
                    "UPDATE transmissions SET status = 'transmitted' WHERE id = ?", (id,)
                )
                connection.commit()
            except Exception:
                # avoid tight loop on unexpected errors; sleep briefly and continue
                time.sleep(1)
    finally:
        try:
            radio_serial.close()
        except Exception:
            pass
        connection.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Serial write interface for ground station")
    parser.add_argument(
        "port",
        nargs="?",
        default="/tmp/radio",
        help="Serial port path to write to (default: /tmp/radio)",
    )
    args = parser.parse_args()
    serial_write(args.port)
