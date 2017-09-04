
# distributed-ledger

A dummy bitcoin simulation.

# setup

## enviornment

We tested the code on Ubuntu 16.04 machines running mininet version 2.2.1

1. The entire design is centered around asynchronous tasks using the asyncio module, so the code requires Python 3.6. 

To install the required Python 3 packages, run:

```
pip3 install --user aioconsole==0.1.3 ecdsa==0.13
```

2. mininet is not available with Python 3, so part of the code also requires Python 2.

To install the required Python 2 packages, run:

```
pip2 install --user mininet==2.2.1
```

3. Apart from this, ensure that mininet is properly setup.

## running the code

In a terminal window, run:

```
sudo python2 start_network.py 10
```

This will spawn 10 nodes (each with a separate xterm.)

The start_network terminal provides a REPL that can be used to modify the network - add, remove nodes etc.

The first spawned xterm has another REPL that allows us to execute RPCs on a host. This can be used to demo money transfer etc.

Both REPL interfaces have a `help` command that lists all available commands and their usage.
