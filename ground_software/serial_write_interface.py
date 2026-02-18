#!/usr/bin/env python3
"""
 @author Lee A. Congdon (lee@silversat.org)
 @author Benjamin S. Cohen (ben@silversat.org)
 @author Dominik Honzak (dominik@silversat.org)
 @brief SilverSat User and radio Doppler interface
 
 This program provides the radio interface for sending commands from the database to the satellite
 
"""

# imports
import argparse
import os
import socket
import sqlite3
import serial
import time
import logging
import sys

BAUD_RATE = 19200
retry_delay = 5  # seconds
NOTIFY_SOCKET_PATH = "/tmp/radio_notify"


def claim_next_transmission(connection, cursor):
    try:
        row = cursor.execute(
            "UPDATE transmissions "
            "SET status = 'sending' "
            "WHERE id = ("
            "  SELECT id FROM transmissions "
            "  WHERE status = 'pending' "
            "  ORDER BY message_sequence ASC LIMIT 1"
            ") "
            "RETURNING id, timestamp, command, status"
        ).fetchone()
        connection.commit()
        return row
    except sqlite3.OperationalError:
        # SQLite without RETURNING support.
        cursor.execute("BEGIN IMMEDIATE")
        row = cursor.execute(
            "SELECT id, timestamp, command, status "
            "FROM transmissions WHERE status='pending' ORDER BY message_sequence ASC LIMIT 1"
        ).fetchone()
        if row is None:
            connection.commit()
            return None

        id, timestamp, command, status = row
        cursor.execute(
            "UPDATE transmissions SET status = 'sending' WHERE id = ? AND status = 'pending'",
            (id,),
        )
        connection.commit()
        if cursor.rowcount == 0:
            return None
        return row


def drain_pending_transmissions(connection, cursor, radio_serial, shutdown_event=None):
    while not (shutdown_event and shutdown_event.is_set()):
        row = claim_next_transmission(connection, cursor)
        if row is None:
            return

        id, timestamp, command, status = row
        radio_serial.write(command)
        cursor.execute(
            "UPDATE transmissions SET status = 'transmitted' WHERE id = ?", (id,)
        )
        connection.commit()


def serial_write(serial_port, shutdown_event=None):
    # open database
    db_path = os.path.abspath("./instance/radio.db")
    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA busy_timeout = 5000")

    notify_socket = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    notify_socket.settimeout(1)
    if os.path.exists(NOTIFY_SOCKET_PATH):
        try:
            os.unlink(NOTIFY_SOCKET_PATH)
        except Exception:
            pass
    notify_socket.bind(NOTIFY_SOCKET_PATH)

    # serial connection
    logging.info("Opening serial port %s @ %d", serial_port, BAUD_RATE)

    radio_serial = None
    while not (shutdown_event and shutdown_event.is_set()):
        try:
            # opening serial connection with a short timeout
            radio_serial = serial.Serial(serial_port, BAUD_RATE, timeout=1)
            break
        except Exception as e:
            print(f"Failed to connect to serial port {serial_port}, retrying in {retry_delay} seconds... ({e})")
            time.sleep(retry_delay)
            continue

    if radio_serial is None:
        notify_socket.close()
        if os.path.exists(NOTIFY_SOCKET_PATH):
            try:
                os.unlink(NOTIFY_SOCKET_PATH)
            except Exception:
                pass
        connection.close()
        return

    try:
        drain_pending_transmissions(connection, cursor, radio_serial, shutdown_event)
        while not (shutdown_event and shutdown_event.is_set()):
            try:
                notify_socket.recv(1)
                drain_pending_transmissions(
                    connection, cursor, radio_serial, shutdown_event
                )
            except socket.timeout:
                continue
            except Exception as exc:
                logging.exception("Serial write loop error: %s", exc)
                time.sleep(1)
    finally:
        try:
            notify_socket.close()
        except Exception:
            pass
        try:
            if os.path.exists(NOTIFY_SOCKET_PATH):
                os.unlink(NOTIFY_SOCKET_PATH)
        except Exception:
            pass
        try:
            radio_serial.close()
        except Exception:
            pass
        connection.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Serial write interface for ground station")
    parser.add_argument(
        "port",
        nargs="?",
        default="/tmp/radio",
        help="Serial port path to write to (default: /tmp/radio)",
    )
    args = parser.parse_args()
    serial_write(args.port)
