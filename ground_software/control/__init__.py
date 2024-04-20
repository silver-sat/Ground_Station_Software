"""
 @file app.py
 @author Lee A. Congdon (lee@silversat.org)
 @brief SilverSat User and radio Doppler interface
 @version 1.0.0
 @date 2023-12-15
 
 This program provides the user interface and the interface to the ground station for radio Doppler data
 
"""

from flask import Flask, render_template, request
import serial
import datetime
import threading

## KISS special characters

FEND = b"\xC0"  # frame end
REMOTE_FRAME = b"\xAA"
DOPPLER_UPLINK = b"\xOD"
DOPPLER_DOWNLINK = b"\xOE"

# Serial link and lock

#command_link = serial.Serial("/dev/serial/by-id/usb-FTDI_FT232R_USB_UART_A50285BI-if00-port0", 57600, timeout=0.5)
serial_link = threading.Lock()

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
    """try:
        transmission = (
            command_link.read_until(expected=FEND)
            + command_link.read_until(expected=FEND)
        )[1:-1]
    except:
        pass
    while transmission:
        if transmission[0] == 0x07:
            transmissions.append(
                f"Beacon: {transmission[1:].decode('utf-8', errors='replace')}"
            )
        else:
            transmissions.append(
                f"{transmission[1:].decode('utf-8', errors='replace')}"
            )
        try:
            transmission = (
                command_link.read_until(expected=FEND)
                + command_link.read_until(expected=FEND)
            )[1:-1]
        except:
            pass"""
    return transmissions


# Application

def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)	
#app = Flask(__name__)

# a simple page that says hello
    @app.route('/hello')
    def hello():
        return 'Hello, World!'

 
# User interface


    @app.route("/", methods=["GET", "POST"])
    def index():
        button = request.form.get("clicked_button")
        serial_link.acquire()
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
                    command_link.write("Call Sign".encode("utf-8"))
                case "Refresh":
                    pass
                case _:
                    pass
            transmissions = get_responses()
            serial_link.release()
            return render_template("control.html", transmissions=transmissions)


    # Radio doppler interface


    @app.post("/radio/uplink")
    def adjust_frequency():
        frequency = request.form.get("frequency")
        serial_link.acquire()
        command_link.write(FEND + DOPPLER_UPLINK + frequency.encode('utf-8') + FEND)
        get_responses()
        serial_link.release()
        return {}
    
    @app.post("/radio/downlink")
    def adjust_frequency():
        frequency = request.form.get("frequency")
        serial_link.acquire()
        command_link.write(FEND + DOPPLER_DOWNLINK + frequency.encode('utf-8') + FEND)
        get_responses()
        serial_link.release()
        return {}
    return app
