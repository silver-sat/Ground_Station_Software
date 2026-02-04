#!/bin/bash

# Accept optional serial port parameter
SERIAL_PORT="${1:-/tmp/radio}"

gpredict &
source .venv/bin/activate
python3 ground_software/ground_station.py "$SERIAL_PORT"
deactivate