#!/usr/bin/env python3
"""
 @file gpredict_radio_interface.py
 @author Lee A. Congdon (lee@silversat.org)
 @author Benjamin S. Cohen (ben@silversat.org)
 @brief SilverSat Ground Station Connection to gpredict
 @version 1.0.0
 @date 2023-12-15
 
 This program provides the interface to the ground station for radio Doppler data
 
"""
import socket
import requests
import datetime

gpredict_address = "127.0.0.1"
gpredict_port = 4532
gpredict_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
gpredict_server.bind((gpredict_address, gpredict_port))
gpredict_server.listen(0)

# Set to address of web server

radio_url = "http://127.0.0.1:8000/radio"

while True:
    print(
        f"gpredict_interface waiting for connection on ",
        {gpredict_address},
        ":",
        {gpredict_port},
    )
    socket, address = gpredict_server.accept()
    print(f"Connected: {address[0], address[1]}")

    receive_frequency = b"000000000"
    transmit_frequency = b"000000000"

    while True:
        data = socket.recv(1024)
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print("Timestamp:", timestamp)
        print("Received:", data)
        command = data[0:1]
        frequency = data[1:].strip()
        match command:

            # set receive frequency
            case b"F":
                receive_frequency = frequency
                print(f"Receive frequency: {frequency}")
                payload = {"frequencies": transmit_frequency + receive_frequency}
                response = requests.post(radio_url, payload)
                socket.sendall(b"RPRT 0\n")

            # get receive frequency
            case b"f":
                print(f"Response: {receive_frequency}")
                socket.sendall(receive_frequency + b"\n")

            # set transmit frequency
            case b"I":
                transmit_frequency = frequency
                print(f"Transmit frequency: {frequency}")
                payload = {"frequencies": transmit_frequency + receive_frequency}
                response = requests.post(radio_url, payload)
                socket.sendall(b"RPRT 0\n")

            # get transmit frequency
            case b"i":
                print(f"Response: {transmit_frequency}")
                socket.sendall(transmit_frequency + b"\n")

            # unknown command
            case _:
                print("Unknown command")
                socket.sendall(b"RPRT 0\n")

    socket.close()
    print(f"Disconnected from: {address[0], address[1]}")
