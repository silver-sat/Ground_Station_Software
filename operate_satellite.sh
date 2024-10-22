#!/bin/bash

gpredict &
source .venv/bin/activate
python3 ground_software/ground_station.py
deactivate