#!/usr/bin/env python3
"""
 @file gpredict_radio_interface.py
 @author Lee A. Congdon (lee@silversat.org)
 @author Ben Cohen (ben@silversat.org)
 @brief SilverSat Ground Station Connection to gpredict
 @version 1.0.0
 @date 2023-12-15
 
 This program provides the interface to the ground station for radio Doppler data
 
"""
import socket
import requests

gpredict_address = "127.0.0.1"
gpredict_port = 4532
gpredict_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
gpredict_server.bind((gpredict_address, gpredict_port))
gpredict_server.listen(0)

radio_url = "http://127.0.0.1:5000/radio"

while True:
    print(
        f"gpredict_interface waiting for connection on ",
        {gpredict_address},
        ":",
        {gpredict_port},
    )
    socket, address = gpredict_server.accept()
    print(f"Connected: {address[0], address[1]}")

    uplink_frequency = 0
    downlink_frequency = 0
    while True:
        data = socket.recv(1024)
        print("worked",data)
        socket.sendall(b"RPRT 0\n")
        if not data:
            break
        # todo: check format of gpredict data
        gpredict_frequency = data[1:].strip()
        if data.startswith(b"F"):
            if gpredict_frequency != uplink_frequency:
                uplink_frequency = gpredict_frequency
                print(f"New uplink frequency: {int(uplink_frequency)}")
                payload = {"frequency": uplink_frequency + downlink_frequency}
                response = requests.post(radio_url, payload)

                socket.sendall(b"RPRT 0\n")
        elif data.startswith(b"f"):
            socket.sendall(bytes(f"f: {int(uplink_frequency)}\n".encode("utf-8")))
        elif data.startswith(b"I"):
            if gpredict_frequency != downlink_frequency:
                downlink_frequency = gpredict_frequency
                print(f"New downlink frequency: {int(downlink_frequency)}")
                payload = {"frequency": uplink_frequency + downlink_frequency}
                response = requests.post(radio_url, payload)
    
            socket.sendall(b"RPRT 0\n")
        elif data.startswith(b"i"):
            socket.sendall(bytes(f"i: {int(downlink_frequency)}\n".encode("utf-8")))
        else:
            print("recieved data", data)
    socket.close()
    print(f"Disconnected from: {address[0], address[1]}")
