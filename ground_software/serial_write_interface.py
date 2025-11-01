#!/usr/bin/env python3
"""
 @author Lee A. Congdon (lee@silversat.org)
 @author Benjamin S. Cohen (ben@silversat.org)
 @author Dominik Honzak (dominik@silversat.org)
 @brief SilverSat User and radio Doppler interface
 
 This program provides the radio interface for sending commands from the database to the satellite
 
"""

# imports
import sqlite3
import serial
import time

BAUD_RATE = 19200
retry_delay = 5  # seconds

def serial_write():

    # open database
    connection = sqlite3.connect("./instance/radio.db")
    cursor = connection.cursor()

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
