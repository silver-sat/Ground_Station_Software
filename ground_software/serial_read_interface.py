#!/usr/bin/env python3
"""
 @file serial_read_interface.py
 @author Lee A. Congdon (lee@silversat.org)
 @author Benjamin S. Cohen (ben@silversat.org)
 @author Dominik Honzak (dominik@silversat.org)
 @brief SilverSat User and radio Doppler interface
 @version 1.0.0
 @date 2024-05-18
 
 This program provides the radio interface for recieving commands
 
"""

# imports
import sqlite3
import serial
import time

BAUD_RATE = 57600
FEND = b"\xC0"


def serial_read():

    # naming serial connection
    serial_port = "/dev/ttys010"

    while True:
        try:
            # opening serial connection
            radio_serial = serial.Serial(serial_port, BAUD_RATE)
            break
        except:
            time.sleep(5)
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
        cursor.execute("INSERT INTO (responses) VALUES (?)", (response,))
        connection.commit()


if __name__ == "__main__":
    serial_read()
