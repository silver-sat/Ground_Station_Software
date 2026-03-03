# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SilverSat Ground Station Software — a Flask web application for commanding a CubeSat over a radio link and receiving telemetry responses. The UI sends commands, the Python backend manages a SQLite queue, and separate threads handle serial I/O and gpredict Doppler control.

## Setup

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install Flask pyserial
flask --app ground_software init-database
```

## Running

```bash
# Full ground station (Flask + all background threads)
python3 -m ground_software.ground_station <portname> --log-port <logportname>

# Or via the convenience script
./operate_satellite.sh <portname> <logportname>
```

Web UI available at http://127.0.0.1:5000.

## Running Tests

```bash
# All tests
python3 -m pytest tests/

# Single test file
python3 -m pytest tests/test_radio_commands.py

# Single test
python3 -m pytest tests/test_radio_commands.py::RadioCommandsTests::test_build_local_command_frame_callsign
```

Tests use `unittest` but are runnable via pytest. The test suite does not require a real serial port — it uses in-memory/temp databases and fakes.

## Database

```bash
# Re-initialize (destructive — drops all tables)
flask --app ground_software init-database

# Non-destructive migration (safe to run on existing data)
flask --app ground_software migrate-database

# Import a saved radio log file
python3 -m ground_software.import_radio_log /path/to/radio_log.txt
```

Database is SQLite at `instance/radio.db`. Schema is in `ground_software/schema.sql`. The `migrate_database()` function in `database.py` is idempotent and runs automatically on every app startup.

## Testing with the Radio Simulator

```bash
# Create a virtual serial link
socat PTY,link=/tmp/ground_station,rawer PTY,link=/tmp/radio,rawer

# Start the simulator (in a separate terminal)
./tests/radio_simulator.py
./tests/radio_simulator.py --fault-profile light
./tests/radio_simulator.py --fault-profile none --force-remote-nack SetClock --seed 42
```

## Architecture

### Process Model

`ground_station.py` spawns Flask as a subprocess and runs four daemon threads, all sharing a `threading.Event` for coordinated shutdown:

| Thread | Module | Role |
|---|---|---|
| gpredict | `gpredict_interface.py` | TCP server on port 4532 for Hamlib/gpredict Doppler data |
| serial_read | `serial_read_interface.py` | Reads KISS frames from radio serial port → inserts into `responses` table |
| serial_write | `serial_write_interface.py` | Claims `pending` rows from `transmissions` table → writes KISS frames to radio |
| serial_log | `serial_log_interface.py` | Reads text lines from log serial port → inserts into `radio_logs` table |

### Command Flow

1. User submits a command via the web UI (`/` or `/radio` routes in `control.py`)
2. `control.sign()` applies HMAC-Blake2s signing with a sequence number and random salt, reading the shared secret from `secret.txt`
3. The signed, KISS-framed command is inserted into the `transmissions` table with status `pending`
4. A Unix datagram socket notification (`/tmp/radio_notify`) wakes the serial write thread
5. The write thread claims the row (sets status to `sending`), writes the frame to the serial port, then marks it `transmitted`
6. The read thread receives the satellite's response KISS frame and inserts it into `responses`
7. The Flask `/responses_stream` endpoint (SSE) polls the database every second and pushes new response rows to the browser

### Database Schema (key tables)

- **`transmissions`** — outgoing command queue; `status` ∈ `{pending, sending, transmitted}`
- **`responses`** — satellite responses received from the serial port
- **`radio_logs`** — text log lines from a separate radio log serial port
- **`settings`** — key/value store; tracks `message_sequence` (global monotonic counter), `command_sequence` (satellite command counter), `responses_cleared_sequence`

All three data tables share a single global `message_sequence` counter (stored in `settings`), making them interleave in chronological order in the `combined_messages` view.

### Key Views (in `schema.sql` / `database.py`)

- **`filtered_transmissions`** — strips KISS framing from commands; excludes local (Doppler) frames
- **`filtered_responses`** — strips KISS framing; excludes `ACK D` / `RES D` diagnostic frames
- **`combined_messages`** — interleaves transmissions, responses, and radio logs by `message_sequence`
- **`radio_log_rssi`** — extracts RSSI dBm values from log lines containing `N: rssi`

### KISS Framing

Commands and responses use KISS framing (`\xC0` as frame delimiter). Remote satellite commands use `\xAA` as the second byte; local radio commands use the command code byte directly.

### Two UI Pages

- **`/` (Operating Interface)** — satellite commands with quick-action buttons; responses shown via SSE stream
- **`/radio` (Radio Commands)** — local radio control commands (RSSI, frequency, CW, sweeps, etc.) with a dropdown command builder; includes an RSSI chart (`/radio/rssi` JSON endpoint)

### Secret File

`secret.txt` in the repository root is the HMAC signing key shared with the satellite's Avionics firmware. It must exist and is listed in `.gitignore`. The path is configurable via `COMMAND_SECRET_PATH` in Flask config.
