#!/usr/bin/env python3
"""
 @file radio_simulator.py
 @author Lee A. Congdon (lee@silversat.org)
 @brief SilverSat Ground Radio Simulator
 @version 1.0.0
 @date 2024-04-22
 
 This program simulates the ground station radio
 
"""

import serial
import time

## KISS special characters

FEND = b"\xC0"  # frame end
REMOTE_FRAME = b"\xAA"
RECEIVE_FREQUENCY = b"\x0D"

# Serial connection

command_link = serial.Serial("/dev/ttys014", 57600)
timer = time.time()

while True:
    try:
        transmission = (
            command_link.read_until(expected=FEND)
            + command_link.read_until(expected=FEND)
        )[1:-1]
    except:
        pass
    print(f"Received: {transmission}")

    # if time.time() - timer > 1:
    #     print("Sending data")
    #     try:
    #         command_link.write(FEND + REMOTE_FRAME + "Data from satellite".encode("utf-8") + FEND)
    #     except:
    #         pass
    #     timer = time.time()
