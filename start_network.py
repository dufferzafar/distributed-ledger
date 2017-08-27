#!/usr/bin/python

import os
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
    os.system("mn --clean")

    if remove_logs:
        for f in os.listdir(config.LOG_DIR):
            os.remove(f)


def xterm_cmd(ip, port, b_ip=None, b_port=None):

    if b_ip:
        title = "Host_%d: "
        file = "start_node.py"
        args = "%s %d %s %d" % (ip, port, b_ip, b_port)
    else:
        title = "Bootstrap CLI: "
        file = "cli.py"
        args = "%s %d" % (ip, port)

    title = "%s %s %d" % (title, ip, port)

    cmd = 'xterm -hold -geometry 130x40+0+900 -title "%s" -e python3 -u "%s" %s &'

    return cmd % (title, file, args)


def start_network(nodes=3):
    global NET

    NET = Mininet(
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

    NET.hosts[0].cmd(c)

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

        host.cmd(c % (i+1))


class MininetREPL(REPL):
    intro = "Control the bitcoin simulation network. Type help or ? to list commands.\n"
    prompt = ">>> "

    def do_stop_network(self, arg):
        """Stop network, close xterms, and exit."""

        print('Quitting now.')

        NET.stop()
        cleanup()
        exit()

    def do_add_node(self, arg):
        """Spawn a new node."""

        host_num = len(NET.hosts) + 1

        end_switch = NET.switches[-1]

        new_switch = NET.addSwitch('s%d' % host_num)
        new_host = NET.addHost("h%d" % host_num)

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

    def do_mn_cli(self, arg):
        """Run mininet CLI."""

        CLI(NET)

if __name__ == '__main__':

    try:

        start_network(
            nodes=int(sys.argv[1])
        )

        MininetREPL().cmdloop()

    except:

        # Helps in debugging
        traceback.print_exc()
        traceback.print_stack()

        cleanup()
