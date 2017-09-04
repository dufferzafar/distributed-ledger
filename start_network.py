#!/usr/bin/python

import os
import re
import sys
import time
import traceback

from cmd import Cmd as REPL

import config

from mininet.net import Mininet
from mininet.cli import CLI
from mininet.link import Link
from mininet.topo import LinearTopo

# The global mininet object
# Created by start_network
# Used by start_control_server
NET = None


def cleanup(remove_logs=False):

    print("Killing all nodes\n")
    os.system("pkill -SIGINT -f '^python3 -u start_node.py'")

    print("Killing all xterms\n")
    os.system("killall -SIGKILL xterm")

    # Call standard mn cleanup
    print("Running standard mininet cleanup command.")
    os.system("mn --clean > /dev/null 2>&1")

    if remove_logs:
        for f in os.listdir(config.LOG_DIR):
            os.remove(f)


def xterm_cmd(ip, port, b_ip=None, b_port=None):

    if b_ip:
        title = "Host_%d: "
        file = "start_node.py"
        args = "%s %d %s %d" % (ip, port, b_ip, b_port)
    else:
        title = "Host_%d - Bootstrap CLI: "
        file = "cli.py"
        args = "%s %d" % (ip, port)

    title = "%s %s %d" % (title, ip, port)

    cmd = 'xterm -hold -geometry 130x40+0+900 -title "%s" -e python3 -u "%s" %s &'

    return cmd % (title, file, args)


def start_network(nodes=3):
    global NET

    NET = Mininet(
        # NOTE: This is actually a SingleTopo
        # Other large topologies hang mininet
        topo=LinearTopo(k=1, n=nodes),
        ipBase=config.IP
    )

    # Start the network
    NET.start()

    # The first node acts as a bootstrapper for other
    c = xterm_cmd(
        ip=NET.hosts[0].IP(),
        port=config.PORT
    )

    NET.hosts[0].cmd(c % 1)

    # Other nodes
    for i, host in enumerate(NET.hosts[1:]):
        # Ensure that each consecutive node is spawned with a slight delay
        # so that no two nodes fight for single actual port (127.0.0.1:port)
        # Every node 10.0.0.*:port is mapped to some 127.0.0.1:port by mininet
        time.sleep(1)

        c = xterm_cmd(
            ip=host.IP(),
            port=config.PORT,
            b_ip=NET.hosts[0].IP(),
            b_port=config.PORT
        )

        host.cmd(c % (i+2))


class MininetREPL(REPL):
    intro = "Control the bitcoin simulation network. Type help or ? to list commands.\n"
    prompt = ">>> "

    def do_EOF(self, line):
        self.do_stop_network(None)

    def do_stop_network(self, line):
        """Stop network, close xterms, and exit."""

        print('Quitting now.')

        NET.stop()
        cleanup()
        exit()

    def do_add_node(self, line):
        """Spawn a new node."""

        host_num = len(NET.hosts) + 1

        end_switch = NET.switches[-1]

        new_switch = NET.addSwitch('s%d' % host_num)
        new_host = NET.addHost("h%ds%d" % (host_num, host_num))

        # TODO: Fix bug that doesn't allow adding nodes starting from 1
        Link(new_host, new_switch)
        slink = Link(end_switch, new_switch)

        end_switch.attach(slink.intf1)

        new_switch.start(NET.controllers)
        new_host.configDefault(defaultRoute=new_host.defaultIntf())

        c = xterm_cmd(
            ip=new_host.IP(),
            port=config.PORT,
            b_ip=NET.hosts[0].IP(),
            b_port=config.PORT
        )

        new_host.cmd(c % host_num)

        print("Started new node: %s" % new_host)

    def do_disconnect_node(self, line):
        """Disconnect a node from the network."""
        args = line.split()
        if (len(args) != 1):
            print("Expected 1 argument, %d given" % len(args))
        else:
            host_name = args[0].strip()
            host_num = int(re.findall(r'\d+', host_name)[0])

            NET.configLinkStatus(host_name, "s%d" % host_num, "down")
            print("Disconnected %s from the network" % host_name)

    def do_reconnect_node(self, line):
        """Re-connect a node to the network."""
        args = line.split()
        if (len(args) != 1):
            print("Expected 1 argument, %d given" % len(args))
        else:
            host_name = args[0].strip()
            host_num = int(re.findall(r'\d+', host_name)[0])

            NET.configLinkStatus(host_name, "s%d" % host_num, "up")
            print("Re-connected %s to the network" % host_name)

    def do_mn_cli(self, line):
        """Run mininet CLI."""

        CLI(NET)

if __name__ == '__main__':

    try:

        start_network(
            nodes=int(sys.argv[1])
        )

        MininetREPL().cmdloop()

    except SystemExit:
        pass

    except:

        # Helps in debugging
        # TODO: Comment these later
        traceback.print_exc()
        traceback.print_stack()

        cleanup()
