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
    redirect,
    render_template,
    request,
    session,
    url_for,
    jsonify,
)
import datetime
from ground_software.database import get_database
import secrets
import hashlib
import hmac

blueprint = Blueprint("control", __name__)

## KISS special characters

FEND = b"\xC0"  # frame end
REMOTE_FRAME = b"\xAA"
CALLSIGN = b"\x0E"

# Command count for sequence number

command_sequence = 1

# Insert command in database


def insert(command):
    database = get_database()
    print(f"Command: {command}")
    command = FEND + REMOTE_FRAME + command + FEND
    database.execute("INSERT INTO transmissions (command) VALUES (?)", (command,))
    database.commit()


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
    database.execute("INSERT INTO transmissions (command) VALUES (?)", (command,))
    database.commit()


# User interface


@blueprint.route("/", methods=["GET", "POST"])
def index():
    global command_sequence
    if request.method == "POST": 
        try:
            command_sequence = int(request.form.get("command_sequence"))
        except ValueError:
            flash("Invalid command sequence value")
        command = request.form.get("command")
        button = request.form.get("clicked_button")
        if command:
            insert(sign(command))
        else:
            match button:
                case "NOP":
                    insert(sign("NoOperate"))
                case "STP":
                    insert(sign("SendTestPacket"))
                case "SRC":
                    insert(sign(f"SetClock {now()}"))
                case "GRC":
                    insert(sign("ReportT"))
                case "PYC":
                    insert(sign("PayComms"))
                case "SPT1":
                    insert(sign(f"PicTimes {now1m()}"))
                case "SBI0":
                    insert(sign("BeaconSp 0"))
                case "SBI1":
                    insert(sign("BeaconSp 60"))
                case "SBI3":
                    insert(sign("BeaconSp 180"))
                case "GTY":
                    insert(sign("GetTelemetry"))
                case "GPW":
                    insert(sign("GetPower"))
                case "CallSign":
                    callsign()
                case "SDT1":
                    insert(sign(f"SSDVTimes {now1m()}"))
                case "Refresh":
                    pass
                case _:
                    pass

    # Update responses
    database = get_database()
    responses = database.execute(
        "SELECT * FROM responses ORDER BY timestamp DESC LIMIT 25"
    ).fetchall()

    return render_template(
        "control.html", responses=responses, command_sequence=command_sequence
    )


@blueprint.route("/latest_responses")
def latest_responses():
    database = get_database()
    responses = database.execute(
        "SELECT * FROM responses ORDER BY timestamp DESC LIMIT 25"
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

    secret = open("secret.txt", "rb").read()
    salt = secrets.token_bytes(8)
    global command_sequence
    sequence = str(command_sequence).zfill(8).encode("utf-8")
    command_sequence = command_sequence + 1
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
