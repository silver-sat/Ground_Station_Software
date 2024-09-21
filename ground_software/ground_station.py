#!/usr/bin/env python3
"""
 @file ground_station.py
 @author Benjamin S. Cohen (ben@silversat.org)
 @brief task manager for ground station
 @version 1.0.0
 @date 2024-06-01
 
task manager for ground station 
"""
import gpredict_interface
import serial_read_interface
import serial_write_interface
import threading
import subprocess


def gpredict_task():
    gpredict_interface.gpredict_read()


def serial_read_task():
    serial_read_interface.serial_read()


def serial_write_task():
    serial_write_interface.serial_write()


if __name__ == "__main__":
    process = subprocess.Popen(["flask", "--app", "ground_software", "run", "--debug"])
    gpredict_thread = threading.Thread(target=gpredict_task)
    serial_read_thread =threading.Thread(target=serial_read_task) 
    serial_write_thread = threading.Thread(target=serial_write_task)
    gpredict_thread.start()
    serial_read_thread.start()
    serial_write_thread.start()
    gpredict_thread.join()
    serial_read_thread.join()
    serial_write_thread.join()
    process.wait()