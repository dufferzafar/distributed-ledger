#!/usr/bin/python

import config
import os
import sys
import time

from mininet.clean import cleanup
from mininet.net import Mininet
from mininet.topo import LinearTopo

BOOT_PORT = 9000


def cleanup_logs():
    for f in os.listdir(config.LOG_DIR):
        os.remove(f)


def start_network(nodes=3):
    topo = LinearTopo(k=1, n=nodes)
    net = Mininet(topo)

    hosts = net.hosts

    # Start the network
    net.start()

    # The first node acts as a bootstrapper for other
    boot_ip = hosts[0].IP()
    hosts[0].cmd(
        'xterm -hold -geometry 130x40+0+900 -title "bootstrap %s %d" -e python3 start_node.py %s %d &' % (
            boot_ip, BOOT_PORT, boot_ip, BOOT_PORT)
    )

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
    start_network(
        nodes=int(sys.argv[1])
    )
