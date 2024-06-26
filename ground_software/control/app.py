"""
 @file app.py
 @author Lee A. Congdon (lee@silversat.org)
 @author Benjamin S. Cohen (ben@silversat.org)
 @brief SilverSat User and radio Doppler interface
 @version 1.0.1
 @date 2023-12-15
 
 This program provides the user interface and the interface to the ground station for radio Doppler data
 
"""

from flask import Flask, render_template, request
import serial
import datetime

## KISS special characters

FEND = b"\xC0"  # frame end
REMOTE_FRAME = b"\xAA"
DOPPLER_FREQUENCIES = b"\x0D"
CALLSIGN = b"\x0E"

# Serial link, set to radio device or test device

# command_link = serial.Serial("/dev/serial/by-id/usb-FTDI_FT232R_USB_UART_A50285BI-if00-port0", 57600, timeout=0.5)
command_link = serial.Serial("/dev/pts/3", 57600, timeout=0.25)
# GMT time formatted for command


def now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y %m %d %H %M %S")


# GMT time in one minute formatted for command


def now1m():
    return (
        datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=60)
    ).strftime("%Y %m %d %H %M %S")


# Issue command


def issue(command):
    try:
        command_link.write(FEND + REMOTE_FRAME + command.encode("utf-8") + FEND)
    except:
        pass


# Get command responses


def get_responses():
    transmissions = []
    global session_transmissions = [] #seems it returns transmissions but this might be easier ...idk
    try:
        transmission = (
            command_link.read_until(expected=FEND)
            + command_link.read_until(expected=FEND)
        )[1:-1]
    except:
        pass
    while transmission:
        transmissions.append(f"{transmission[1:].decode('utf-8', errors='replace')}")
        session_transmissions.append(f"{transmission[1:].decode('utf-8', errors='replace')}") #hopefully this is right -dom
        try:
            transmission = (
                command_link.read_until(expected=FEND)
                + command_link.read_until(expected=FEND)
            )[1:-1]
        except:
            pass
    return transmissions


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
            issue(command)
        else:
            match button:
                case "NOP":
                    issue("NoOperate")
                case "STP":
                    issue("SendTestPacket")
                case "SRC":
                    issue(f"SetClock {now()}")
                case "GRC":
                    issue("ReportT")
                case "PYC":
                    issue("PayComms")
                case "SPT1":
                    issue(f"PicTimes {now1m()}")
                case "SBI1":
                    issue("BeaconSp 60")
                case "SBI3":
                    issue("BeaconSp 180")
                case "GTY":
                    issue("GetTelemetry")
                case "GPW":
                    issue("GetPower")
                case "CallSign":
                    command_link.write(FEND + CALLSIGN + FEND)
                case "Refresh":
                    pass
                case _:
                    pass
        # transmissions = get_responses()
        print("Exiting index")
        transmissions = []
        return render_template("control.html", transmissions=transmissions)

    # Radio doppler interface

    @app.post("/radio")
    def adjust_frequencies():
        frequencies = request.form.get("frequencies")
        print("Sending: " + frequencies)
        command_link.write(
            FEND + DOPPLER_FREQUENCIES + frequencies.encode("utf-8") + FEND
        )
        # get_responses()
        return {}

    return app
