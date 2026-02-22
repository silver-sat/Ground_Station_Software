# Ground Control Software

The ground control software presents a user interface for issuing commands to the satellite and receiving responses. It also forwards gpredict radio Doppler data to adjust the receive and transmit frequencies for the ground radio.

The ground control software is a web application developed in Flask to send commands and display responses and Python modules to read from gpredict, write to the radio, and read from the radio. Commands and responses are queued and stored in a sqlite3 database.

## Installing the User and Radio Interface

These instructions assume a Linux or MacOS environment. Different steps would be required for Windows environments.

Clone the Ground_Station_Software repository from github to a local directory on the laptop. If the repository is already present, ensure it is up to date using git pull from the command line or the equivalent.

Open a command shell and navigate to the Ground_Station_Software directory. Create a python virtual environment with the following command:

```python3 -m venv .venv```

Activate the virtual environment with:

```. .venv/bin/activate```

Note that the .venv directory is a hidden file (it starts with "."), so you may have to use command line options or change the settings of your file manager to see it in a file listing.

Now install Flask using this command:

```pip install Flask```

and optionally install Waitress with this command:

```pip install waitress```

(Waitress is not used in the current configuration. It is planned for use in the production configuration to enable remote access. The Flask test server is not secure.)

Install pyserial using this command

```pip install pyserial```

Now initialize the database with the following command

```flask --app ground_software init-database```

This will create the radio.db database in the instance folder, which is used to store commands and responses.

### One-time import of a radio log file (testing/development)

If you have a saved text radio log file and want to load it once into `radio_logs`:

```python3 -m ground_software.import_radio_log /path/to/radio_log.txt```

This importer uses today's date and the `HH:MM:SS` time embedded in each log line to populate the `timestamp` column, and it allocates `message_sequence` values from the current database sequence.

Optional arguments:

```python3 -m ground_software.import_radio_log /path/to/radio_log.txt --db ./instance/radio.db --log-date 2026-02-15```

`--log-date` sets the calendar date used with each embedded `HH:MM:SS` log time.

Lines that do not contain an `HH:MM:SS` time are skipped and reported.

## Installing the Radio Doppler Control

Install the gpredict application on the laptop by following the instructions for your operating system. Homebrew is recommended for MacOS and apt is recommended for Ubuntu.

The gpredict_interface.py module provides the functions of Hamlib rigctld daemon. You do not need rigctld to control the SilverSat radio.

Launch gpredict, configure your location as the default and add a radio. The radio should be Duplex TRX with PTT status None. Update the satellite tracking information (the TLE data). Ensure you have data for SilverSat available in the gpredict application.

## Verifying the Shared Secret

Create a secret.txt file in the Ground_Station_Software directory that matches the arduino_secrets.h file used to compile the Avionics software. Ensure that this file is included in .gitignore to prevent it from being uploaded to github.

## Starting the Ground Station

From the Ground_Station_Software directory, execute

```python3 -m ground_software.ground_station portname --log-port logportname```

where *portname* is the name of the serial port for the radio and *logportname* is the serial port that emits text radio log lines (optional, default `/tmp/radio_log`). This will start the gpredict interface module, the serial read task, the serial write task, the serial radio log task, and the user interface. The gpredict interface will listen on the default TCP/IP port used by gpredict for radio frequency information.

Use `Ctrl+C` (or send `SIGTERM`) to stop all tasks with graceful shutdown.

Open a browser and navigate to the address displayed in the Flask startup log, typically http://127.0.0.1:5000/. Ensure the SilverSat user interface is displayed. 

You may now enter commands to the satellite by clicking a button or typing a command on the command line and pressing enter. Responses from the satellite will be displayed at the bottom of the window, most recent response first.
The UI receives response updates through a persistent server-sent events stream (`/responses_stream`) rather than periodic browser polling.

Start gpredict and open Radio Control. Target SilverSat and Track it. Then select your radio device and Engage. Radio Doppler data for the selected satellite will be transmitted to the ground radio via the gpredict interface module.

## Operating the satellite

With the setup steps above completed, you can operate the satellite with these steps.

1. In a terminal, navigate to the Ground_Station_Software directory and run ```./operate_satellite.sh portname logportname``` where *portname* is the name of the radio serial port and *logportname* is the optional serial port for radio text logs.

5. Track and engage the satellite using the gpredict interface.

6. Start a browser and navigate to http://127.0.0.1:5000.

You may now interact with the satellite using the browser interface and monitor its location using the gpredict interface.

## Security considerations

The Flask development server is not secured for network deployment. However, it can be used to locally control the satellite. To enable remote access, the application has been tested on Waitress. The application does not authenticate users and should only be used via a VPN.
