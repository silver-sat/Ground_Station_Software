"""
 @file control.py
 @author Lee A. Congdon (lee@silversat.org)
 @author Benjamin S. Cohen (ben@silversat.org)
 @brief SilverSat User and radio Doppler interface
 @version 1.0.0
 @date 2024-04-30
 
 This program provides the user interface
 
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
)

from flask import Flask, render_template, request
import datetime
from ground_software.database import get_database

blueprint = Blueprint("control", __name__)

## KISS special characters

FEND = b"\xC0"  # frame end
REMOTE_FRAME = b"\xAA"
CALLSIGN = b"\x0E"

# Insert command in database


def insert(command):
    database = get_database()
    print(f"Command: {command}")
    command = FEND + REMOTE_FRAME + command.encode("utf-8") + FEND
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
    button = request.form.get("clicked_button")
    command = request.form.get("command")
    if button == None and command != None:
        insert(command)
    else:
        match button:
            case "NOP":
                insert("NoOperate")
            case "STP":
                insert("SendTestPacket")
            case "SRC":
                insert(f"SetClock {now()}")
            case "GRC":
                insert("ReportT")
            case "PYC":
                insert("PayComms")
            case "SPT1":
                insert(f"PicTimes {now1m()}")
            case "SBI1":
                insert("BeaconSp 60")
            case "SBI3":
                insert("BeaconSp 180")
            case "GTY":
                insert("GetTelemetry")
            case "GPW":
                insert("GetPower")
            case "CallSign":
                callsign()
            case "Refresh":
                pass
            case _:
                pass
    
    database = get_database()
    responses = database.execute(
        "SELECT * FROM responses ORDER BY timestamp DESC LIMIT 100"
    ).fetchall()
    return render_template("control.html", responses=responses)
