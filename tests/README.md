# Ground Control Software Testing

You can test the ground station software using the radio simulator. The radio simulator sends and receives data on a serial port, just as the actual ground radio does.

## Installing and Creating the Serial Port

Install socat using the instructions for your operating system. socat is used to create two linked serial ports that simulate the serial connection to and from the radio. 

Open a terminal. Enter the command to create the serial link:

```socat PTY,link=/tmp/ground_station,rawer PTY,link=/tmp/radio,rawer```

Start the radio simulator:

```./tests/radio_simulator.py```

Optional fault injection examples:

```./tests/radio_simulator.py --fault-profile light```

```./tests/radio_simulator.py --fault-profile none --force-remote-nack SetClock --force-local-res-err D --seed 42```

Fault profile options:

- `--fault-profile {none,light,moderate,aggressive}`
- `--remote-nack-rate <0..1>` and `--remote-res-err-rate <0..1>`
- `--local-nack-rate <0..1>` and `--local-res-err-rate <0..1>`
- `--drop-response-rate <0..1>`
- `--force-remote-nack <comma-separated command names>`
- `--force-remote-res-err <comma-separated command names>`
- `--force-local-nack <comma-separated local command codes>`
- `--force-local-res-err <comma-separated local command codes>`
- `--seed <int>` for repeatable randomized behavior

Open a new terminal. Start the ground station software:

```./operate_satellite.sh```

Track and engage a satellite using the gpredict interface.

Start a browser. Navigate to http://127.0.0.1:5000

You may now interact with the software using the browser interface.

You can open another terminal to examine the contents of the database using sqlite3 or use a tool of your choice.