# Ground Control Software

The ground control software presents a user interface for entering commands to the satellite and receiving responses. It also enables the use of gpredict radio Doppler data to adjust the receive and transmit frequencies for the ground radio.

The ground control software is a web application developed in Flask to send commands and receive responses and Python modules to read from gpredict, write to the radio, and read from the radio. Commands and responses are queued and stored in a sqlite3 database.

## Installing the User and Radio Interface

Clone the Ground_Station_Software repository from github to a local directory on the laptop. If the repository is already present, ensure it is up to date using git pull or the equivalent.

Open a command shell and navigate to the ground_software directory in the FlatSat directory. Create a python virtual environment with the following command

```python3 -m venv .venv```

Activate the virtual environment with 

```. .venv/bin/activate```

Note that the .venv directory is a hidden file (it starts with "."), so you may have to use command line options or change the settings of your file manager to see it in a file listing.

Now install Flask using this command

```pip install Flask```

and install Waitress with this command

```pip install waitress```

Install pyserial using this command

```pip install pyserial```

Now initialize the database with the following command

```flask --app __init__ init-database```

Set the appropriate value for the radio serial port in the serial_read_interface and serial_write_interface modules.

## Installing the Radio Doppler Control

Install the gpredict application on the laptop following the instructions for your operating system.

The gpredict_interface.py module provides the functions of Hamlib rigctld daemon. You do not need rigctld to control the SilverSat radio.

Launch gpredict, configure your location and add a radio. The radio should be Duplex TRX with PTT status None. Insure you have data for SilverSat and its initial frequencies available in the application.

## Starting the Ground Station

From the ground_software directory, execute

```./ground_station.py```

This will start the gpredict interface, the serial read task, the serial write task, and the user interface. The gpredict interface will listen on the default TCP/IP port used by gpredict for radio frequency information.

If you receive an error message, you may need to modify the serial port name in serial_read_interface.py and serial_write_interface.py to match the port name of the radio on your system.

Open a browser and navigate to the address displayed, typically http://127.0.0.1:5000/.
Insure the SilverSat user interface is displayed. You may now enter commands to the satellite by clicking a button or typing a command on the command line and pressing enter. Responses from the satellite will be displayed.

Start gpredict and open Radio Control. Target SilverSat and Track it. Then select your radio device and Engage. Radio Doppler data for the selected satellite will be transmitted to the ground radio. The frequencies will be visible in the command window.

## Security considerations

The Flask development server is not secured for network deployment. However, it can be used to locally control the satellite. To enable remote access, the application has been tested on Waitress. The application does not authenticate users and should only be used via a VPN.
