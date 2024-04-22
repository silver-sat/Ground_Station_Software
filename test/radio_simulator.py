#!/usr/bin/env python3
"""
 @file app.py
 @author Lee A. Congdon (lee@silversat.org)
 @brief SilverSat Ground Radio Simulator
 @version 1.0.0
 @date 2024-04-22
 
 This program simulates ground station radio
 
"""

import serial

## KISS special characters

FEND = b"\xC0"  # frame end
REMOTE_FRAME = b"\xAA"
TRANSMIT_FREQUENCY = b"\x0D"
RECEIVE_FREQUENCY = b"\x0E"

# Serial connection

command_link = serial.Serial("/dev/ttys016", 57600)

while True:
    try:
        transmission = (
            command_link.read_until(expected=FEND)
            + command_link.read_until(expected=FEND)
        )[1:-1]
    except:
        pass
    print(f"Received: {transmission}")