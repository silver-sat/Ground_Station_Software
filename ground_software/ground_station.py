#!/usr/bin/env python3
"""
 @author Benjamin S. Cohen (ben@silversat.org)
 @brief task manager for ground station

task manager for ground station
"""
import argparse
import threading
import subprocess

from ground_software import gpredict_interface
from ground_software import serial_log_interface
from ground_software import serial_read_interface
from ground_software import serial_write_interface


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
    parser.add_argument(
        "--log-port",
        default="/tmp/radio_log",
        help="Serial port path for radio text log interface (default: /tmp/radio_log)",
    )
    args = parser.parse_args()
    port = args.port
    log_port = args.log_port

    process = subprocess.Popen(["flask", "--app", "ground_software", "run", "--debug"])

    gpredict_thread = threading.Thread(target=gpredict_task)
    serial_read_thread = threading.Thread(
        target=serial_read_interface.serial_read, args=(port,)
    )
    serial_write_thread = threading.Thread(
        target=serial_write_interface.serial_write, args=(port,)
    )
    serial_log_thread = threading.Thread(
        target=serial_log_interface.serial_log_read, args=(log_port,)
    )

    gpredict_thread.start()
    serial_read_thread.start()
    serial_write_thread.start()
    serial_log_thread.start()

    gpredict_thread.join()
    serial_read_thread.join()
    serial_write_thread.join()
    serial_log_thread.join()
    process.wait()