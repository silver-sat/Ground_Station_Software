# Ground Control Software Testing

You can test the ground station software using the radio simulator. The radio simulator sends and receives data on a serial port, just as the actual ground radio does.

## Installing and Creating the Serial Port

Install socat using the instructions for your operating system. socat is used to create two linked serial ports that simulate the serial connection to and from the radio. 

Open a terminal. Enter the command to create the serial link:

```socat PTY,link=/tmp/ground_station,rawer PTY,link=/tmp/radio,rawer```

Start the radio simulator:

```./tests/radio_simulator.py```

Open a new terminal. Start the ground station software:

```./operate_satellite.sh```

Track and engage a satellite using the gpredict interface.

Start a browser. Navigate to http://127.0.0.1:5000

You may now interact with the software using the browser interface.

You can open another terminal to examine the contents of the database using sqlite3 or use a tool of your choice.