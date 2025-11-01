#!/usr/bin/env python3
"""
 @author Lee A. Congdon (lee@silversat.org)
 @author Benjamin S. Cohen (ben@silversat.org)
 @author Dominik Honzak (dominik@silversat.org)
 @brief SilverSat User and radio Doppler interface
 
 This program provides the radio interface for receiving responses and storing them in the database
 
"""

# imports
import sqlite3
import serial
import time

BAUD_RATE = 19200
retry_delay = 5  # seconds
FEND = b"\xC0"


def serial_read():

    # serial connection
    # serial_port = "/dev/tty.usbserial-AL062R13"
    serial_port = "/tmp/radio"

    while True:
        try:
            # opening serial connection
            radio_serial = serial.Serial(serial_port, BAUD_RATE)
            break
        except:
            print(f"Failed to connect to serial port {serial_port}, retrying in {retry_delay} seconds...")
            time.sleep(retry_delay)
            continue

    # open database

    connection = sqlite3.connect("instance/radio.db")
    cursor = connection.cursor()
    # read the responses from the radio
    while True:
        try:
            response = radio_serial.read_until(expected=FEND) + radio_serial.read_until(
                expected=FEND
            )

        except:
            break
        cursor.execute("INSERT INTO responses (response) VALUES (?)", (response,))
        connection.commit()


if __name__ == "__main__":
    serial_read()
