#!/usr/bin/env python3
"""
 @file gpredict_interface.py
 @author Lee A. Congdon (lee@silversat.org)
 @author Benjamin S. Cohen (ben@silversat.org)
 @brief SilverSat Ground Station Software
 @version 1.0.0
 @date 2024-04-29
 
 This program provides the interface to gpredict for the ground station
 
"""

# KISS special characters

FEND = b"\xC0"  # frame end
DOPPLER_FREQUENCIES = b"\x0D"

# Read Doppler data from gpredict


def gpredict_read():

    import socket
    import sqlite3

    # gpredict network configuration
    gpredict_address = "127.0.0.1"
    gpredict_port = 4532
    gpredict_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    gpredict_server.bind((gpredict_address, gpredict_port))
    gpredict_server.listen(0)

    # Open the database

    connection = sqlite3.connect("instance/radio.db")
    cursor = connection.cursor()

    # Wait for gpredict connection

    while True:
        print(
            f"gpredict_interface waiting for connection on {gpredict_address}:{gpredict_port}"
        )
        socket, address = gpredict_server.accept()
        print(f"Connected: {address[0], address[1]}")

        # todo: set initial receive and transmit frequencies
        receive_frequency = b"000000000"
        transmit_frequency = b"000000000"

        # Process gpredict commands

        while True:

            # read data from gpredict

            try:
                data = socket.recv(1024)
            except:
                socket.close()
                print(f"Error on: {address[0], address[1]}")
                break

            # parse command and frequency

            command = data[:1]
            frequency = data[1:].strip()

            match command:

                # set receive frequency
                case b"F":
                    receive_frequency = frequency
                    cursor.execute(
                        "INSERT INTO transmissions (command) VALUES (?)",
                        (
                            FEND
                            + DOPPLER_FREQUENCIES
                            + transmit_frequency
                            + receive_frequency
                            + FEND,
                        ),
                    )
                    connection.commit()
                    try:
                        socket.sendall(b"RPRT 0\n")
                    except:
                        socket.close()
                        print(f"Error on: {address[0], address[1]}")
                        break

                # get receive frequency
                case b"f":
                    try:
                        socket.sendall(receive_frequency + b"\n")
                    except:
                        socket.close()
                        print(f"Error on: {address[0], address[1]}")
                        break

                # set transmit frequency
                case b"I":
                    transmit_frequency = frequency
                    cursor.execute(
                        "INSERT INTO transmissions (command) VALUES (?)",
                        (
                            FEND
                            + DOPPLER_FREQUENCIES
                            + transmit_frequency
                            + receive_frequency
                            + FEND,
                        ),
                    )
                    connection.commit()
                    try:
                        socket.sendall(b"RPRT 0\n")
                    except:
                        socket.close()
                        print(f"Error on: {address[0], address[1]}")
                        break

                # get transmit frequency
                case b"i":
                    try:
                        socket.sendall(transmit_frequency + b"\n")
                    except:
                        socket.close()
                        print(f"Error on: {address[0], address[1]}")
                        break

                # unknown command
                case _:
                    print(f"Unknown command: {data}")
                    try:
                        socket.sendall(b"RPRT 0\n")
                    except:
                        socket.close()
                        print(f"Error on: {address[0], address[1]}")
                        break


if __name__ == "__main__":
    gpredict_read()
