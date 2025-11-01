#!/usr/bin/env python3
"""
Simple serial radio simulator for tests.

Behavior:
- Listens on a serial device.
- When it receives data that starts with FEND + DOPPLER_FREQUENCIES (b'\xC0\x0D')
  it replies first with ACK + DOPPLER_FREQUENCIES, then sends
  RES + DOPPLER_FREQUENCIES + <transmit_frequency> + SPACE + <receive_frequency> + FEND

Usage:
    python tests/extended_radio_simulator.py --port /dev/ttyUSB0
    (options: --baud, --tx, --rx, --once)
"""
import argparse
import logging
import time

try:
    import serial
except Exception:
    serial = None

# constants mirror gpredict_interface
FEND = b"\xC0"
DOPPLER_FREQUENCIES = b"\x0D"
SPACE = b"\x20"

BAUD_RATE = 19200

DEFAULT_TX = b"433000000"
DEFAULT_RX = b"433001000"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")


def run_sim(port, baud=BAUD_RATE, transmit=DEFAULT_TX, receive=DEFAULT_RX, once=False, timeout=1.0):
    if serial is None:
        logging.error("pyserial not installed. Install with: pip install pyserial")
        return

    logging.info("Opening serial port %s @ %d", port, baud)
    ser = serial.Serial(port, baudrate=baud, timeout=timeout)
    try:
        buf = b""
        while True:
            # read whatever is available
            data = ser.read(1024)
            if not data:
                # no data this cycle
                if once:
                    break
                continue

            buf += data
            logging.debug("Received raw bytes: %r", data)

            # if buffer contains message starting with FEND + DOPPLER_FREQUENCIES
            # we check for that prefix at any position (incoming frames may include preceding bytes)
            idx = buf.find(FEND + DOPPLER_FREQUENCIES)
            if idx == -1:
                # keep buffer from growing unbounded: keep last 32 bytes
                if len(buf) > 4096:
                    buf = buf[-32:]
                if once:
                    break
                continue

            # consume up through the found prefix (simulate handling)
            buf = buf[idx:]
            logging.info("Detected frame prefix at buffer index %d", idx)

            # send ACK + DOPPLER_FREQUENCIES
            ack = b"ACK" + DOPPLER_FREQUENCIES
            try:
                ser.write(ack)
                ser.flush()
                logging.info("Sent ACK frame: %r", ack)
            except Exception as e:
                logging.error("Error writing ACK: %s", e)
                break

            # small delay before sending RES frame
            time.sleep(0.05)

            # send RES + DOPPLER_FREQUENCIES + transmit + SPACE + receive + FEND
            res = b"RES" + DOPPLER_FREQUENCIES + transmit + SPACE + receive + FEND
            try:
                ser.write(res)
                ser.flush()
                logging.info("Sent RES frame: %r", res)
            except Exception as e:
                logging.error("Error writing RES: %s", e)
                break

            # consume the processed buffer to avoid re-triggering on same bytes
            buf = b""
            if once:
                break

    finally:
        logging.info("Closing serial port")
        ser.close()


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Extended radio simulator for tests")
    p.add_argument("--port", "-p", required=True, help="Serial device path (e.g. /dev/ttyUSB0 or COM3)")
    p.add_argument("--baud", "-b", type=int, default=9600, help="Baud rate")
    p.add_argument("--tx", default=DEFAULT_TX.decode("ascii"), help="Transmit frequency bytes (ascii digits)")
    p.add_argument("--rx", default=DEFAULT_RX.decode("ascii"), help="Receive frequency bytes (ascii digits)")
    p.add_argument("--once", action="store_true", help="Handle one incoming frame then exit")
    args = p.parse_args()

    run_sim(
        port=args.port,
        baud=args.baud,
        transmit=args.tx.encode("ascii"),
        receive=args.rx.encode("ascii"),
        once=args.once,
    )