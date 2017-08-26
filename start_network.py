#!/usr/bin/python

import os
import sys
import socket
import time

import config

from mininet.net import Mininet
from mininet.topo import LinearTopo

BOOT_PORT = 9000

# The global mininet object
# Created by start_network
# Used by start_mininet_control_server
NET = None


def cleanup(remove_logs=False):

    print("Killing all nodes\n")
    os.system("pkill -SIGINT -f '^python3 -u start_node.py'")

    print("Killing all xterms\n")
    os.system("killall -SIGKILL xterm")

    # Call standard mn cleanup
    os.system("mn --clean")

    if remove_logs:
        for f in os.listdir(config.LOG_DIR):
            os.remove(f)


def xterm_cmd(ip, port, b_ip=None, b_port=None):

    if b_ip:
        title = "Host_%d: " % (port - b_port)
        file = "start_node.py"
    else:
        title = "Bootstrap CLI: "
        file = "cli.py"

    title = "%s %s %d" % (title, ip, port)
    args = "%s %d" % (ip, port)

    cmd = 'xterm -hold -geometry 130x40+0+900 -title "%s" -e python3 -u "%s" %s &'

    return cmd % (title, file, args)


def start_network(nodes=3):
    global NET

    NET = Mininet(LinearTopo(k=1, n=nodes))
    hosts = NET.hosts

    # Start the network
    NET.start()

    # The first node acts as a bootstrapper for other
    c = xterm_cmd(
        ip=hosts[0].IP(),
        port=BOOT_PORT)
    hosts[0].cmd(c)

    # Other nodes
    for i, host in enumerate(hosts[1:]):
        # Ensure that each consecutive node is spawned with a slight delay
        # so that no two nodes fight for single actual port (127.0.0.1:port)
        # Every node 10.0.0.*:port is mapped to some 127.0.0.1:port by mininet
        time.sleep(1)

        c = xterm_cmd(
            ip=host.IP(),
            port=BOOT_PORT + i + 1,
            b_ip=hosts[0].IP(),
            b_port=BOOT_PORT
        )
        host.cmd(c)


def start_mininet_control_server():

    print("Mininet Control Server is now running. Press Ctrl+C to exit.")

    # Create & bind to a UDP socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, 0)
    # s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    s.bind(config.MN_CONTROLLER_SOCKET)

    while True:
        cmd = s.recv(512).strip()

        print(cmd)
        if cmd == "stop":
            print("Stop Message Received. Quitting Now.")

            NET.stop()
            cleanup()

            exit()


if __name__ == '__main__':

    try:

        start_network(nodes=int(sys.argv[1]))

        start_mininet_control_server()

    except KeyboardInterrupt:
        cleanup()
