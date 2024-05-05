#!/usr/bin/env python3
"""
 @file serial_read_interface.py
 @author Lee A. Congdon (lee@silversat.org)
 @author Benjamin S. Cohen (ben@silversat.org)
 @brief SilverSat Ground Station read radio serial interface
 @version 1.0.0
 @date 2024-04-29
 
 This program provides the interface to read responses from the radio for the ground station
 
"""

FEND = b"\xC0"  # frame end


def serial_read():

    import sqlite3
    import serial
    import time

    # Open the serial port to the radio

    serial_port = "/dev/ttys010"
    print(f"Opening serial port: {serial_port} for reading")
    while True:
        try:
            radio_serial = serial.Serial(serial_port, 57600)
            print(f"Serial port: {serial_port} opened for reading")
            break
        except:
            print(f"Error opening serial port: {serial_port} for reading")
            time.sleep(5)
            continue

    # Open the database

    connection = sqlite3.connect("instance/radio.db")
    cursor = connection.cursor()

    # Read responses from the radio

    while True:

        try:
            response = radio_serial.read_until(expected=FEND) + radio_serial.read_until(
                expected=FEND
            )
        except:
            print(f"Error on: {radio_serial}")
            break

        cursor.execute("INSERT INTO responses (response) VALUES (?)", (response,))
        connection.commit()


if __name__ == "__main__":
    serial_read()
