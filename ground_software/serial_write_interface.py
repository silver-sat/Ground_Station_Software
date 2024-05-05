#!/usr/bin/env python3
"""
 @file serial_write_interface.py
 @author Lee A. Congdon (lee@silversat.org)
 @author Benjamin S. Cohen (ben@silversat.org)
 @brief SilverSat Ground Station write radio serial interface
 @version 1.0.0
 @date 2024-04-29
 
 This program provides the interface to write commands to the radio for the ground station
 
"""


def serial_write():

    import sqlite3
    import serial
    import time

    # Open the database

    connection = sqlite3.connect("instance/radio.db")
    cursor = connection.cursor()

    # Open the serial port to the radio

    serial_port = "/dev/ttys010"
    print(f"Opening serial port: {serial_port} for writing")
    while True:
        try:
            radio_serial = serial.Serial(serial_port, 57600)
            print(f"Serial port: {serial_port} opened for writing")
            break
        except:
            print(f"Error opening serial port: {serial_port} for writing")
            time.sleep(5)
            continue

    # Read responses from the database and write to the radio
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
