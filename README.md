# Ground Control Software

The ground control software presents a user interface for entering commands to the satellite and receiving responses. It also enables the use of gpredict radio Doppler data to adjust the transmit and receive frequencies for the ground radio.

The ground control software is a web application developed in Flask. The Flask development server is not secured for network deployment. However, it can be used to locally control the satellite. To enable remote access, the application has been tested on Waitress. The application does not authenticate users and should only be used via a VPN.

## Installing the User Interface

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

Now move to the control directory in the ground_software directory and enter the following command

```Flask run --debug```

for development and testing or the following command for production

```waitress-serve --listen=127.0.0.1:5000 --call app:create_app``` 

This starts the web application in the folder. If you receive an error message, you may need to modify the serial port name in app.py to match the port name on your system.

Open a browser and navigate to the address displayed, typically http://127.0.0.1:5000/

You may now enter commands to the satellite by clicking a button or typing a command on the command line.

## Installing the Radio Doppler Control

Install the gpredict application on the laptop following the instructions for the operating system.

The gpredict_radio_interface.py program in the radio folder and the Flask web application provide the functions of Hamlib rigctld daemon. You do not need rigctld to control the radio frequencies.

Open a new command window, navigate to the radio folder, and enter the command

```gpredict_radio_interface.py```

The program will listen on the default TCP/IP port used by gpredict for radio frequency information.

Now launch gpredict, add a radio as explained in the User Manual, open the radio interface, select a satellite in Target and track it. Verify that the Flask or Waitress application is running. Select your radio in Settings and engage it. Radio Doppler data for the selected satellite will be transmitted to the ground radio. The frequencies will be visible in the command window.
