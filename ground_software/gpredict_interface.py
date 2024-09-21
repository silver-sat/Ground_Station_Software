#!/usr/bin/env python3
"""
 @file gpredict_interface.py
 @author Lee A. Congdon (lee@silversat.org)
 @author Benjamin S. Cohen (ben@silversat.org)
 @brief provides GPredict interface for the ground station
 @version 1.0.0
 @date 2024-06-01
 
 This program provides the GPredict interface for the ground station
 
"""
FEND = b"\xC0"
DOPPLER_FREQUENCIES = b"\x0D"


def gpredict_read():
    import sqlite3
    import socket

    gpredict_address = "127.0.0.1"
    gpredict_port = 4532
    gpredict_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    gpredict_server.bind((gpredict_address, gpredict_port))
    gpredict_server.listen(0)
    connection = sqlite3.connect("./instance/radio.db")
    cursor = connection.cursor()
    while True:
        print(
            f"Gpredict waiting for a connection on: {gpredict_address}:{gpredict_port}"
        )
        socket, address = gpredict_server.accept()
        print(f"connected: {address[0],address[1]}")
        receive_frequency = b"00000000"
        transmit_frequency = b"00000000"
        while True:

            try:
                data = socket.recv(1024)
            except:
                socket.close()
                print(f"Error on {address[0],address[1]}")
                break
            command = data[:1]
            frequency = data[1:].strip()
            print(f"command {command} frequency {frequency}")
            match command:
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
                        print(f"Error on {address[0],address[1]}")
                        break
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
                        print(f"Error on {address[0],address[1]}")
                        break
                case b"i":
                    try:
                        socket.sendall(transmit_frequency + b"\n")
                    except:
                        socket.close()
                        print(f"Error on {address[0],address[1]}")
                        break
                case b"f":
                    try:
                        socket.sendall(receive_frequency + b"\n")
                    except:
                        socket.close()
                        print(f"Error on {address[0],address[1]}")
                        break
                        
                case _:
                    print(f"unknown command: {data}")
                    try:    
                        socket.sendall(b"RPRT 0\n")
                    except:
                        socket.close()
                        print(f"Error on {address[0],address[1]}")
                        break
if __name__ == "__main__":
    gpredict_read()
                    
