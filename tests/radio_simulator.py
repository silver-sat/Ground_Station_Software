#!/usr/bin/env python3
"""
 @author Lee A. Congdon (lee@silversat.org)
 @brief SilverSat Ground Radio Simulator
 
 This program simulates the ground station radio
 
"""

import serial
import time
import threading

## KISS special characters

FEND = b"\xC0"  # frame end
REMOTE_FRAME = b"\xAA"
RECEIVE_FREQUENCY = b"\x0D"

# Serial connection

BAUD_RATE = 19200

command_link = serial.Serial("/dev/ground_station", BAUD_RATE)
print("Radio simulator started")

def reader(): 
    while True:
        try:
            transmission = (
                command_link.read_until(expected=FEND)
                + command_link.read_until(expected=FEND)
            )[1:-1]
            print(f"Received data: {transmission}")
        except:
            pass

def writer():
    timer = time.time()
    counter = 1
    while True:
        if time.time() - timer > 1:
            print("Sending data")
            try:
                command_link.write(FEND + REMOTE_FRAME + f"Data from satellite {counter}".encode("utf-8") + FEND)
            except:
                pass
            timer = time.time()
            counter += 1

if __name__ == "__main__":
    read_thread = threading.Thread(target=reader)
    write_thread = threading.Thread(target=writer)

    read_thread.start()
    write_thread.start()

    read_thread.join()
    write_thread.join()