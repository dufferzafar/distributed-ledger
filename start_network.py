#!/usr/bin/python

import config
import os
import sys
import time

from mininet.clean import cleanup
from mininet.net import Mininet

BOOT_PORT = 9000


def cleanup_logs():
    for f in os.listdir(config.LOG_DIR):
        os.remove(f)


def start_network(nodes=3):
    hosts = []
    net = Mininet()
    s0 = net.addSwitch('s0')  # central switch

    # Adding hosts
    for i in range(0, nodes):
        host = net.addHost('h%s' % i)

        # Link the host to the switch
        net.addLink(host, s0)
        hosts.append(host)

    net.addController('c0')

    # Start the network
    net.start()

    # The first node acts as a bootstrapper for other
    hosts[0].cmd(
        'xterm -hold -geometry 130x40+0+900 -title "bootstrap %s %d" -e python3 start_node.py %s %d &' % (
            hosts[0].IP(), BOOT_PORT, hosts[0].IP(), BOOT_PORT)
    )

    boot_ip = hosts[0].IP()

    # Other nodes
    port = BOOT_PORT + 1
    for i, host in enumerate(hosts[1:]):
        host.cmd('xterm -hold -geometry 130x40+0+900 -title "host_%d %s %d" -e python3 -u start_node.py %s %d %s %d &' %
                 (i + 1, host.IP(), port, host.IP(), port, boot_ip, BOOT_PORT))

        # Ensure that each node is spawned with a slight delay
        # so that no two nodes fight for single actual port (127.0.0.1:port)
        time.sleep(1)

        # Every node 10.0.0.*:port is mapped to some 127.0.0.1:port
        # by mininet ?
        port += 1

    raw_input('Press enter to stop all nodes.')

    print("Killing all nodes\n")
    os.system("killall -SIGINT python3")

    print("Killing all xterms\n")
    os.system("killall -SIGINT xterm")

    net.stop()
    cleanup()

if __name__ == '__main__':
    start_network(nodes=sys.argv[1])
