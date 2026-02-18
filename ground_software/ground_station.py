#!/usr/bin/env python3
"""
 @author Benjamin S. Cohen (ben@silversat.org)
 @brief task manager for ground station

task manager for ground station
"""
import argparse
import threading
import subprocess
import signal
import time

from ground_software import gpredict_interface
from ground_software import serial_log_interface
from ground_software import serial_read_interface
from ground_software import serial_write_interface


def gpredict_task(shutdown_event):
    gpredict_interface.gpredict_read(shutdown_event=shutdown_event)


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

    shutdown_event = threading.Event()

    process = subprocess.Popen(["flask", "--app", "ground_software", "run", "--debug"])

    gpredict_thread = threading.Thread(target=gpredict_task, args=(shutdown_event,))
    serial_read_thread = threading.Thread(
        target=serial_read_interface.serial_read, args=(port, shutdown_event)
    )
    serial_write_thread = threading.Thread(
        target=serial_write_interface.serial_write, args=(port, shutdown_event)
    )
    serial_log_thread = threading.Thread(
        target=serial_log_interface.serial_log_read, args=(log_port, shutdown_event)
    )

    threads = [
        gpredict_thread,
        serial_read_thread,
        serial_write_thread,
        serial_log_thread,
    ]

    def request_shutdown(signum=None, frame=None):
        shutdown_event.set()

    signal.signal(signal.SIGINT, request_shutdown)
    signal.signal(signal.SIGTERM, request_shutdown)

    for thread in threads:
        thread.start()

    try:
        while not shutdown_event.is_set():
            if process.poll() is not None:
                shutdown_event.set()
                break
            if not any(thread.is_alive() for thread in threads):
                shutdown_event.set()
                break
            time.sleep(0.2)
    finally:
        shutdown_event.set()
        for thread in threads:
            thread.join(timeout=3)

        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)