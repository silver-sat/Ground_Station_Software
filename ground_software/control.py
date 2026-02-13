"""
 @author Lee A. Congdon (lee@silversat.org)
 @author Benjamin S. Cohen (ben@silversat.org)
 @author Dominik Honzak (dominik@silversat.org)
 @brief SilverSat User and radio Doppler interface
 
 This program provides the user interface for sending commands and receiving responses
 
"""

from flask import (
    Blueprint,
    flash,
    g,
    current_app,
    redirect,
    render_template,
    request,
    session,
    url_for,
    jsonify,
)
import datetime
import socket
from ground_software.database import get_database
import secrets
import hashlib
import hmac
import os

blueprint = Blueprint("control", __name__)

## KISS special characters

FEND = b"\xC0"  # frame end
REMOTE_FRAME = b"\xAA"
CALLSIGN = b"\x0E"
NOTIFY_SOCKET_PATH = "/tmp/radio_notify"

# Cached signing secret

_SIGNING_SECRET = None

# Insert command in database


def insert(command):
    database = get_database()
    print(f"Command: {command}")
    command = FEND + REMOTE_FRAME + command + FEND
    message_sequence = next_message_sequence()
    database.execute(
        "INSERT INTO transmissions (message_sequence, command) VALUES (?, ?)",
        (message_sequence, command),
    )
    database.commit()
    notify_transmission()


# Get UTC as a string


def now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y %m %d %H %M %S")


# Get UTC as a string for 1 minute in the future


def now1m():
    return (
        datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=60)
    ).strftime("%Y %m %d %H %M %S")


# Insert callsign command in database


def callsign():
    database = get_database()
    command = FEND + CALLSIGN + FEND
    message_sequence = next_message_sequence()
    database.execute(
        "INSERT INTO transmissions (message_sequence, command) VALUES (?, ?)",
        (message_sequence, command),
    )
    database.commit()
    notify_transmission()


def notify_transmission():
    try:
        notify_socket = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        notify_socket.connect(NOTIFY_SOCKET_PATH)
        notify_socket.send(b"\x00")
    except Exception:
        pass
    finally:
        try:
            notify_socket.close()
        except Exception:
            pass


def get_current_command_sequence():
    database = get_database()
    row = database.execute(
        "SELECT value FROM settings WHERE key = ?", ("command_sequence",)
    ).fetchone()
    if row and row["value"] is not None:
        try:
            return int(row["value"])
        except (TypeError, ValueError):
            return 1
    return 1


def set_command_sequence(sequence_value):
    if sequence_value is None:
        raise ValueError("Missing command sequence value")

    sequence = int(sequence_value)
    if sequence < 0:
        raise ValueError("Sequence value must be non-negative")

    database = get_database()
    database.execute(
        "INSERT INTO settings (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        ("command_sequence", str(sequence)),
    )
    database.commit()


def next_command_sequence():
    database = get_database()
    try:
        database.execute("BEGIN IMMEDIATE")
        row = database.execute(
            "SELECT value FROM settings WHERE key = ?", ("command_sequence",)
        ).fetchone()
        if row and row["value"] is not None:
            try:
                current_sequence = int(row["value"])
            except (TypeError, ValueError):
                current_sequence = 1
        else:
            current_sequence = 1

        database.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            ("command_sequence", str(current_sequence + 1)),
        )
        database.commit()
        return current_sequence
    except Exception:
        database.rollback()
        raise


def next_message_sequence():
    database = get_database()
    try:
        database.execute("BEGIN IMMEDIATE")
        row = database.execute(
            "SELECT value FROM settings WHERE key = ?", ("message_sequence",)
        ).fetchone()
        if row and row["value"] is not None:
            try:
                current_sequence = int(row["value"])
            except (TypeError, ValueError):
                current_sequence = 1
        else:
            current_sequence = 1

        database.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            ("message_sequence", str(current_sequence + 1)),
        )
        database.commit()
        return current_sequence
    except Exception:
        database.rollback()
        raise


def get_signing_secret():
    global _SIGNING_SECRET
    if _SIGNING_SECRET is not None:
        return _SIGNING_SECRET

    secret_path = current_app.config.get("COMMAND_SECRET_PATH", "secret.txt")
    try:
        with open(secret_path, "rb") as secret_file:
            _SIGNING_SECRET = secret_file.read()
    except FileNotFoundError as error:
        raise RuntimeError(
            f"Signing secret file not found at {secret_path}. "
            "Create secret.txt or set COMMAND_SECRET_PATH."
        ) from error

    if not _SIGNING_SECRET:
        raise RuntimeError(f"Signing secret file at {secret_path} is empty")

    return _SIGNING_SECRET

# Persist the "clear responses" sequence in the database

def clear_responses():
    database = get_database()
    row = database.execute(
        "SELECT COALESCE(MAX(message_sequence), 0) AS max_sequence FROM responses"
    ).fetchone()
    cleared_sequence = row["max_sequence"] if row else 0
    database.execute(
        "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
        ("responses_cleared_sequence", str(cleared_sequence)),
    )
    database.commit()


# User interface


@blueprint.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST": 
        command = request.form.get("command")
        button = request.form.get("clicked_button")
        if button == "SetSequence":
            try:
                set_command_sequence(request.form.get("command_sequence"))
            except ValueError:
                flash("Invalid command sequence value")
        elif command:
            try:
                insert(sign(command))
            except RuntimeError as error:
                flash(str(error))
        else:
            match button:
                case "NOP":
                    try:
                        insert(sign("NoOperate"))
                    except RuntimeError as error:
                        flash(str(error))
                case "STP":
                    try:
                        insert(sign("SendTestPacket"))
                    except RuntimeError as error:
                        flash(str(error))
                case "SRC":
                    try:
                        insert(sign(f"SetClock {now()}"))
                    except RuntimeError as error:
                        flash(str(error))
                case "GRC":
                    try:
                        insert(sign("ReportT"))
                    except RuntimeError as error:
                        flash(str(error))
                case "PYC":
                    try:
                        insert(sign("PayComms"))
                    except RuntimeError as error:
                        flash(str(error))
                case "SPT1":
                    try:
                        insert(sign(f"PicTimes {now1m()}"))
                    except RuntimeError as error:
                        flash(str(error))
                case "SBI0":
                    try:
                        insert(sign("BeaconSp 0"))
                    except RuntimeError as error:
                        flash(str(error))
                case "SBI1":
                    try:
                        insert(sign("BeaconSp 60"))
                    except RuntimeError as error:
                        flash(str(error))
                case "SBI3":
                    try:
                        insert(sign("BeaconSp 180"))
                    except RuntimeError as error:
                        flash(str(error))
                case "GTY":
                    try:
                        insert(sign("GetTelemetry"))
                    except RuntimeError as error:
                        flash(str(error))
                case "GPW":
                    try:
                        insert(sign("GetPower"))
                    except RuntimeError as error:
                        flash(str(error))
                case "CallSign":
                    callsign()
                case "SDT1":
                    try:
                        insert(sign(f"SSDVTimes {now1m()}"))
                    except RuntimeError as error:
                        flash(str(error))
                case "ClearResponses":
                    clear_responses()
                case _:
                    pass

    # Render template

    return render_template(
        "control.html", responses=[], command_sequence=get_current_command_sequence()
    )


@blueprint.route("/latest_responses")
def latest_responses():
    # get cleared sequence if it exists
    database = get_database()
    row = database.execute(
        "SELECT value FROM settings WHERE key = ?", ("responses_cleared_sequence",)
    ).fetchone()
    if row and row["value"]:
        cleared_sequence = int(row["value"])
        responses = database.execute(
            "SELECT * FROM responses "
            "WHERE message_sequence > ? AND CAST(substr(response, 3, 5) AS TEXT) NOT IN ('RES D','ACK D') "
            "ORDER BY message_sequence DESC LIMIT 25",
            (cleared_sequence,),
        ).fetchall()
    else:
        responses = database.execute(
            "SELECT * FROM responses "
            "WHERE CAST(substr(response, 3, 5) AS TEXT) NOT IN ('RES D','ACK D') "
            "ORDER BY message_sequence DESC LIMIT 25"
        ).fetchall()
    return jsonify(
        [
            {
                "timestamp": row["timestamp"],
                "response": row["response"].decode("utf-8", errors="replace"),
            }
            for row in responses
        ]
    )


# Generate signed command


def sign(command):
    secret = get_signing_secret()
    salt = secrets.token_bytes(8)
    sequence = str(next_command_sequence()).zfill(8).encode("utf-8")
    command = command.encode("utf-8")
    computed_hmac = hmac.new(secret, digestmod=hashlib.blake2s)
    computed_hmac.update(salt)
    computed_hmac.update(sequence)
    computed_hmac.update(command)
    signature = (
        computed_hmac.hexdigest().encode("utf-8")
        + salt.hex().encode("utf-8")
        + sequence
    )
    return signature + command
