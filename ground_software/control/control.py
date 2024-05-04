"""
 @file control.py
 @author Lee A. Congdon (lee@silversat.org)
 @author Benjamin S. Cohen (ben@silversat.org)
 @brief SilverSat User and radio Doppler interface
 @version 1.0.1
 @date 2023-12-15
 
 This program provides the user interface
 
"""

from flask import (
    Flask,
    render_template,
    request,
    Blueprint,
    flash,
    g,
    redirect,
    render_template,
    session,
    url_for,
)
import datetime
from ground_software.database import get_database

blueprint = Blueprint("control", __name__)
## KISS special characters

FEND = b"\xC0"  # frame end
REMOTE_FRAME = b"\xAA"
CALLSIGN = b"\x0E"


def insert(command):
    database = get_database()
    command = FEND + REMOTE_FRAME + command + FEND
    database.execute("INSERT INTO transmissions (command) VALUES (?)", (command,))
    database.commit()


def now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y %m %d %H %M %S")


# GMT time in one minute formatted for command


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




# Application


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)

    # a simple page that says hello
    @app.route("/hello")
    def hello():
        return "Hello, World!"

    # User interface

    @app.route("/", methods=["GET", "POST"])
    def index():
        print("Entering index")
        button = request.form.get("clicked_button")
        if button == None:
            command = request.form.get("command")
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
        database=get_database()
        responses=database.execute("SELECT * FROM responses ORDER BY timestamp DESC LIMIT 100").fetchall()        
        print("Exiting index")
        return render_template("control.html", responses=responses)


    return app
