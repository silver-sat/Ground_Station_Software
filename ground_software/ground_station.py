#!/usr/bin/env python3
"""
 @file ground_station.py
 @author Lee A. Congdon (lee@silversat.org)
 @author Benjamin S. Cohen (ben@silversat.org)
 @brief SilverSat Ground Station Software
 @version 1.0.0
 @date 2024-04-29
 
 This program provides the interface to the ground station for radio Doppler data and the user interface
 
"""

import subprocess
import threading
import gpredict_interface
import serial_read_interface
import serial_write_interface


def gpredict_task():
    gpredict_interface.gpredict_read()


def serial_read_task():
    serial_read_interface.serial_read()


def serial_write_task():
    serial_write_interface.serial_write()


if __name__ == "__main__":

    # Start the user interface

    proc = subprocess.Popen(
        ["flask", "--app", "ground_software", "run", "--debug", "--port", "8000"]
    )

    # Create and start the threads for the gpredict, serial read, and serial write interfaces

    gpredict_thread = threading.Thread(target=gpredict_task)
    serial_read_thread = threading.Thread(target=serial_read_task)
    serial_write_thread = threading.Thread(target=serial_write_task)

    gpredict_thread.start()
    serial_read_thread.start()
    serial_write_thread.start()

    # Wait for all threads to finish
    # todo: implement clean shutdown
    gpredict_thread.join()
    serial_read_thread.join()
    serial_write_thread.join()
    proc.wait()
