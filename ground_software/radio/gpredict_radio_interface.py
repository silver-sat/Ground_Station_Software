#!/usr/bin/env python3
'''
 @file gpredict_radio_interface.py
 @author Lee A. Congdon (lee@silversat.org)
 @brief SilverSat Ground Station Connection to gpredict
 @version 1.0.0
 @date 2023-12-15
 
 This program provides the interface to the ground station for radio Doppler data
 
'''
import socket
import requests

gpredict_address = '127.0.0.1'
gpredict_port = 4532
gpredict_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
gpredict_server.bind((gpredict_address, gpredict_port))
gpredict_server.listen(0)

url = "http://127.0.0.1:5000/radio"

while True:
    print(f'gpredict_interface waiting for connection on ', {gpredict_address}, ':', {gpredict_port})
    socket, address = gpredict_server.accept()
    print(f'Connected: {address[0], address[1]}')

    current_frequency = 0
    while True:
        data = socket.recv(1024)
        if not data:
            break
        if data.startswith(b'F'):
            frequency = data[1:].strip()
            if current_frequency != frequency:
                print(f'New frequency: {int(frequency)}')
                payload = {'frequency':frequency}
                response = requests.post(url, payload)
                current_frequency = frequency
            socket.sendall(b'RPRT 0\n')
        elif data.startswith(b'f'):
            socket.sendall(bytes(f'f: {int(current_frequency)}\n'.encode("utf-8")))
    socket.close()
    print(f'Disconnected from: {address[0], address[1]}')
