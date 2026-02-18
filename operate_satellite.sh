#!/bin/bash

# Accept optional serial port parameter
SERIAL_PORT="${1:-/tmp/radio}"
LOG_SERIAL_PORT="${2:-/tmp/radio_log}"

gpredict &
source .venv/bin/activate
python3 -m ground_software.ground_station "$SERIAL_PORT" --log-port "$LOG_SERIAL_PORT"
deactivate