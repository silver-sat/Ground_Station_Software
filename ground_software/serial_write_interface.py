#!/usr/bin/env python3
"""
 @author Lee A. Congdon (lee@silversat.org)
 @author Benjamin S. Cohen (ben@silversat.org)
 @author Dominik Honzak (dominik@silversat.org)
 @brief SilverSat User and radio Doppler interface
 
 This program provides the radio interface for sending commands
 
"""

# imports
import sqlite3
import serial
import time

BAUD_RATE = 19200


def serial_write():

    # open database
    connection = sqlite3.connect("./instance/radio.db")
    cursor = connection.cursor()

    # naming serial connection
    serial_port = "/dev/ground_radio"

    while True:
        try:
            # opening serial connection
            radio_serial = serial.Serial(serial_port, BAUD_RATE)
            break
        except:
            time.sleep(5)
            continue

    while True:
        try:
            result = cursor.execute(
                "SELECT * FROM transmissions WHERE status='pending' ORDER BY id ASC LIMIT 1"
            )
            id, timestamp, command, status = result.fetchone()
            radio_serial.write(command)
            cursor.execute(
                "UPDATE transmissions SET status = 'transmitted' WHERE id = ?", (id,)
            )
            connection.commit()
        except:
            time.sleep(1)


if __name__ == "__main__":
    serial_write()
