#!/usr/bin/python

import os
import time
import config

from mininet.clean import cleanup
from mininet.net import Mininet

BOOT_PORT = 9000
MAX_NODES = 3


def cleanup_logs():
    for f in os.listdir(config.LOG_DIR):
        os.remove(f)


def main():
    hosts = []
    net = Mininet()
    s0 = net.addSwitch('s0')  # central switch

    # adding hosts
    for id in range(0, MAX_NODES):
        host = net.addHost('h%s' % id)
        net.addLink(host, s0)
        hosts.append(host)

    net.addController('c0')

    net.start()

    # first node without bootstrap
    hosts[0].cmd(
        'xterm -hold -geometry 130x40+0+900 -title "bootstrap %s %d" -e python3 start_node.py %s %d &' % (
            hosts[0].IP(), BOOT_PORT, hosts[0].IP(), BOOT_PORT)
    )

    boot_ip = hosts[0].IP()

    # rest of the nodes
    port = BOOT_PORT + 1
    for i, host in enumerate(hosts[1:]):
        host.cmd('xterm -hold -geometry 130x40+0+900 -title "host_%d %s %d" -e python3 -u start_node.py %s %d %s %d &' %
                 (i + 1, host.IP(), port, host.IP(), port, boot_ip, BOOT_PORT))
        # delay to ensure each node is spawned at a slightly different timed so that no two nodes fight for single actual port (127.0.0.1:port)
        time.sleep(1)
        # every node 10.0.0.*:port is mapped to some 127.0.0.1:port
        port += 1

    raw_input('Press enter to stop all nodes.')
    print ("Killing all nodes\n")
    # to kill all start_node inside every terminal
    os.system("killall -SIGINT python3")
    print ("Killing all xterms\n")
    os.system("killall -SIGINT xterm")  # to kill all xterms
    net.stop()
    cleanup()

if __name__ == '__main__':
    main()
