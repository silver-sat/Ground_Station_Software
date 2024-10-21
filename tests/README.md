# Ground Control Software Testing

You can test the ground station software using the radio simulator. The radio simulator sends and receives data on a serial port, just as the acutal ground radio does.

## Installing and Creating the Serial Port

Install socat using the instructions for your operating system. socat is used to create two linked serial ports that simulate the serial connection to and from the radio. 

Enter the command to create the serial link:

```socat PTY,link=/tmp/ground_station,raw,echo=0 PTY,link=/tmp/ground_radio,raw,echo=0```

Open a new terminal. Navigate to the Ground_Station_Software directory.

Start the radio simulator:

```