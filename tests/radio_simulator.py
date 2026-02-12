#!/usr/bin/env python3
"""
 @author Lee A. Congdon (lee@silversat.org)
 @brief SilverSat Ground Radio Simulator
 
 This program simulates the ground station radio
 
"""

import logging
import serial
import time

## KISS special characters

FEND = b"\xC0"  # frame begin/end
LOCAL_COMMAND = b"\x00"
AVIONICS_DATA = b"\xAA"
DOPPLER_FREQUENCIES = b"\x0D"
CALLSIGN = b"\x0E"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logging.info("Starting radio simulator")

# Serial connection
PORT = "/tmp/ground_station"
BAUD_RATE = 19200
RETRY_DELAY_SECONDS = 2
logging.info("Opening serial port %s @ %d", PORT, BAUD_RATE)


def open_serial_with_retry(port, baud_rate):
    while True:
        try:
            return serial.Serial(port, baud_rate, timeout=1)
        except Exception as error:
            logging.warning(
                "Unable to open %s yet (%s). Retrying in %d seconds...",
                port,
                error,
                RETRY_DELAY_SECONDS,
            )
            time.sleep(RETRY_DELAY_SECONDS)


ground_station = open_serial_with_retry(PORT, BAUD_RATE)


def read_kiss_payload(serial_connection):
    while True:
        first = serial_connection.read(1)
        if not first:
            return None
        if first == FEND:
            break

    payload = serial_connection.read_until(expected=FEND)
    if not payload:
        return None
    if payload[-1:] != FEND:
        return None
    return payload[:-1]

def processor():
    sequence_number = 0
    while True:
        try:
            transmission = read_kiss_payload(ground_station)
            if not transmission:
                continue
            logging.debug("Received frame payload: %r", transmission)
        except Exception:
            continue

        # Using match (Python 3.10+), with guards for prefix checks
        match transmission:
            case _ if transmission.startswith(AVIONICS_DATA):
                logging.info("Detected AVIONICS_DATA frame")
                # simulate response from satellite (ground radio does not ACK or RESpond)
                sequence_number += 1
                ack = FEND + AVIONICS_DATA + b"ACK " + str(sequence_number).encode() + FEND
                try:
                    ground_station.write(ack)  # ACK frame
                    ground_station.flush()
                    logging.debug("Sent ACK frame: %r", ack)
                except Exception as e:
                    logging.error("Error writing ACK: %s", e)
                    break
                res = FEND + AVIONICS_DATA + b"RES XXX" + FEND
                try:
                    ground_station.write(res)  # RES frame
                    ground_station.flush()
                    logging.debug("Sent RES frame: %r", res)
                except Exception as e:
                    logging.error("Error writing RES: %s", e)
                    break
            case _ if transmission.startswith(DOPPLER_FREQUENCIES):
                logging.debug("Detected DOPPLER_FREQUENCIES frame")
                ack = FEND + LOCAL_COMMAND + b"ACK D" + FEND
                try:
                    ground_station.write(ack)  # ACK frame
                    ground_station.flush()
                    logging.debug("Sent ACK frame: %r", ack)
                except Exception as e:
                    logging.error("Error writing ACK: %s", e)
                    break
                res = FEND + LOCAL_COMMAND + b"RES D123456789 123456789" + FEND
                try:
                    ground_station.write(res)  # RES frame
                    ground_station.flush()
                    logging.debug("Sent RES frame: %r", res)
                except Exception as e:
                    logging.error("Error writing RES: %s", e)
                    break
            case _ if transmission.startswith(CALLSIGN):
                logging.info("Detected CALLSIGN frame")
                ack = FEND + LOCAL_COMMAND + b"ACK E" + FEND
                try:
                    ground_station.write(ack)  # ACK frame
                    ground_station.flush()
                    logging.debug("Sent ACK frame: %r", ack)
                except Exception as e:
                    logging.error("Error writing ACK: %s", e)
                    break
                # handle callsign...
            case _:
                logging.debug("Unknown frame")

if __name__ == "__main__":
    processor()