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
import sqlite3
import serial
import time
import sys

BAUD_RATE = 19200
retry_delay = 5  # seconds
FEND = b"\xC0"


def serial_read(serial_port):
    """Read from the given serial_port and write responses to the database."""
    while True:
        try:
            # opening serial connection
            radio_serial = serial.Serial(serial_port, BAUD_RATE)
            break
        except Exception:
            print(f"Failed to connect to serial port {serial_port}, retrying in {retry_delay} seconds...")
            time.sleep(retry_delay)
            continue

    # open database
    connection = sqlite3.connect("instance/radio.db")
    cursor = connection.cursor()

    # read the responses from the radio
    try:
        while True:
            try:
                response = radio_serial.read_until(expected=FEND) + radio_serial.read_until(expected=FEND)
            except Exception:
                break
            cursor.execute("INSERT INTO responses (response) VALUES (?)", (response,))
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
