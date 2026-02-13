#!/usr/bin/env python3
"""
 @author Lee A. Congdon (lee@silversat.org)
 @author Benjamin S. Cohen (ben@silversat.org)
 @brief provides GPredict interface for the ground station
 
 This program provides the GPredict interface for the ground station
 
"""
import sqlite3
import socket
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")

# Character codes
FEND = b"\xC0"
DOPPLER_FREQUENCIES = b"\x0D"
SPACE = b"\x20"

# Configuration
initial_frequency = b"433000000"
alternate_frequency = b"433001000"
test_doppler = False
gpredict_address = "127.0.0.1"
gpredict_port = 4532
gpredict_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)


def next_message_sequence(connection, cursor):
    cursor.execute("BEGIN IMMEDIATE")
    row = cursor.execute(
        "SELECT value FROM settings WHERE key = ?", ("message_sequence",)
    ).fetchone()
    if row and row[0] is not None:
        try:
            current_sequence = int(row[0])
        except (TypeError, ValueError):
            current_sequence = 1
    else:
        current_sequence = 1

    cursor.execute(
        "INSERT INTO settings (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        ("message_sequence", str(current_sequence + 1)),
    )
    connection.commit()
    return current_sequence


def database_write(transmit_frequency, receive_frequency):
    """Write the doppler transaction to the database"""
    try:
        connection = sqlite3.connect("./instance/radio.db")
        cursor = connection.cursor()
        message_sequence = next_message_sequence(connection, cursor)
        cursor.execute(
            "INSERT INTO transmissions (message_sequence, command) VALUES (?, ?)",
            (
                message_sequence,
                FEND
                + DOPPLER_FREQUENCIES
                + transmit_frequency
                + SPACE
                + receive_frequency
                + FEND,
            ),
        )
        connection.commit()
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    except Exception as e:
        print(f"Exception in database_write: {e}")
    finally:
        if connection:
            connection.close()


def gpredict_write(socket, message):
    """Write a message to gpredict"""
    try:
        socket.sendall(message)
    except Exception as e:
        print(f"Error on gpredict write: {e}")
        socket.close()


def process_command(command, frequency, socket, transmit_frequency, receive_frequency):
    """Process the comman from gpredict"""
    match command:
        case b"F":
            receive_frequency = frequency
            database_write(transmit_frequency, receive_frequency)
            gpredict_write(socket, b"RPRT 0\n")
        case b"I":
            transmit_frequency = frequency
            database_write(transmit_frequency, receive_frequency)
            gpredict_write(socket, b"RPRT 0\n")
        case b"i":
            gpredict_write(socket, transmit_frequency + b"\n")
        case b"f":
            gpredict_write(socket, receive_frequency + b"\n")
        case _:
            logging.warning(f"unknown command: {command}")
            gpredict_write(socket, b"RPRT 1\n")
    return transmit_frequency, receive_frequency


def gpredict_read():
    """Manage the gpredict interface"""
    gpredict_server.bind((gpredict_address, gpredict_port))
    gpredict_server.listen(0)
    while True:
        logging.info(
            f"Gpredict interface waiting for a connection on: {gpredict_address}:{gpredict_port}"
        )
        socket, address = gpredict_server.accept()
        logging.info(f"Connected: {address[0],address[1]}")
        receive_frequency = initial_frequency
        transmit_frequency = initial_frequency
        test_frequency = initial_frequency

        while True:
            try:
                data = socket.recv(1024)
                if not data:
                    break
            except Exception as e:
                logging.error(f"Error receiving data: {e}")
                socket.close()
                break

            command = data[:1]
            frequency = data[1:].strip()
            logging.info(f"command {command} frequency {frequency}")

            transmit_frequency, receive_frequency = process_command(
                command, frequency, socket, transmit_frequency, receive_frequency
            )

            if test_doppler:
                if test_frequency != initial_frequency:
                    test_frequency = initial_frequency
                else:
                    test_frequency = alternate_frequency
                database_write(test_frequency, test_frequency)

        socket.close()
        logging.info(f"Disconnected: {address[0],address[1]}")


if __name__ == "__main__":
    gpredict_read()
