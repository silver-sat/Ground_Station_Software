#!/usr/bin/env python3
"""
 @author Benjamin S. Cohen (ben@silversat.org)
 @brief task manager for ground station

task manager for ground station
"""
import argparse
import threading
import subprocess

import gpredict_interface
import serial_read_interface
import serial_write_interface


def gpredict_task():
    gpredict_interface.gpredict_read()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ground station task manager")
    parser.add_argument(
        "port",
        nargs="?",
        default="/tmp/radio",
        help="Serial port path for read/write interfaces (default: /tmp/radio)",
    )
    args = parser.parse_args()
    port = args.port

    process = subprocess.Popen(["flask", "--app", "ground_software", "run", "--debug"])

    gpredict_thread = threading.Thread(target=gpredict_task)
    serial_read_thread = threading.Thread(
        target=serial_read_interface.serial_read, args=(port,)
    )
    serial_write_thread = threading.Thread(
        target=serial_write_interface.serial_write, args=(port,)
    )

    gpredict_thread.start()
    serial_read_thread.start()
    serial_write_thread.start()

    gpredict_thread.join()
    serial_read_thread.join()
    serial_write_thread.join()
    process.wait()