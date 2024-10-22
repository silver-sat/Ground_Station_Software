# Ground Control Software

The ground control software presents a user interface for entering commands to the satellite and receiving responses. It also transmits gpredict radio Doppler data to adjust the receive and transmit frequencies for the ground radio.

The ground control software is a web application developed in Flask to send commands and display responses and Python modules to read from gpredict, write to the radio, and read from the radio. Commands and responses are queued and stored in a sqlite3 database.

## Installing the User and Radio Interface

These instructions assume a Linux or MacOS environment. Different steps would be required for Windows environments.

Clone the Ground_Station_Software repository from github to a local directory on the laptop. If the repository is already present, ensure it is up to date using git pull from the command line or an equivalent.

Open a command shell and navigate to the Ground_Station_Software directory. Create a python virtual environment with the following command:

```python3 -m venv .venv```

Activate the virtual environment with:

```. .venv/bin/activate```

Note that the .venv directory is a hidden file (it starts with "."), so you may have to use command line options or change the settings of your file manager to see it in a file listing.

Now install Flask using this command:

```pip install Flask```

and install Waitress with this command:

```pip install waitress```

(Waitress is not used in the test configuration. It is planned for use in the production configuration to enable remote access. The Flask test server is not secure.)

Install pyserial using this command

```pip install pyserial```

Now initialize the database with the following command

```flask --app ground_software init-database```

This will create the radio.db database in the instance folder to store commands and responses.

Set the appropriate value for the radio serial port in the serial_read_interface and serial_write_interface modules. You may find it convenient to use socat to connect a PTY to the actual port to avoid changing the code.

## Installing the Radio Doppler Control

Install the gpredict application on the laptop by following the instructions for your operating system.

The gpredict_interface.py module provides the functions of Hamlib rigctld daemon. You do not need rigctld to control the SilverSat radio.

Launch gpredict, configure your location as the default and add a radio. The radio should be Duplex TRX with PTT status None. Update the satellite tracking information (the TLE data). Ensure you have data for SilverSat available in the gpredict application.

## Verifying the Shared Secret

Create a secret.txt file in the Ground_Station_Software directory that matches the arduino_secrets.h file used to compile the Avionics software. Ensure that this file is included in .gitignore to prevent it from being uploaded to github.

## Starting the Ground Station

From the Ground_Station_Software directory, execute

```./ground_software/ground_station.py```

This will start the gpredict interface module, the serial read task, the serial write task, and the user interface. The gpredict interface will listen on the default TCP/IP port used by gpredict for radio frequency information.

If you receive an error message, you may need to modify the serial port name in serial_read_interface.py and serial_write_interface.py to match the port name of the radio on your system. Again, socat may allow you to map the serial port to a defined PTY name.

Open a browser and navigate to the address displayed in the Flask startup log, typically http://127.0.0.1:5000/. Ensure the SilverSat user interface is displayed. 

You may now enter commands to the satellite by clicking a button or typing a command on the command line and pressing enter. Responses from the satellite will be displayed at the bottom of the window, most recent response first.

Start gpredict and open Radio Control. Target SilverSat and Track it. Then select your radio device and Engage. Radio Doppler data for the selected satellite will be transmitted to the ground radio via the gpredict interface module. The frequencies will be visible in the command window.

## Operating the satellite

With the setup steps above completed, you can operate the satellite with these steps.

1. In a terminal, navigate to the Ground_Station_Software directory and run ```./operate_satellite.sh```.

5. Track and engage the satellite using the gpredict interface.

6. Start a browser and navigate to http://127.0.0.1:5000.

You may now interact with the satellite using the browser interface and monitor its location using the gpredict interface.

## Security considerations

The Flask development server is not secured for network deployment. However, it can be used to locally control the satellite. To enable remote access, the application has been tested on Waitress. The application does not authenticate users and should only be used via a VPN.
