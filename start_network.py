#!/usr/bin/python

import time
# from mininet.topo import Topo
from mininet.net import Mininet
from mininet.util import dumpNodeConnections
from mininet.log import setLogLevel

BOOT_PORT = 9000
LOCALHOST = "127.0.0.1"
MAX_NODES = 3

def test():
    hosts = []
    net = Mininet()
    s0 = net.addSwitch('s0') #central switch

    #adding hosts
    for id in range(0, MAX_NODES):
        host = net.addHost('h%s' % id)
        net.addLink(host, s0)
        hosts.append(host)

    c0 = net.addController('c0') #whats the role of controller?

    net.start()

    # first node without bootstrap
    cmd_out = hosts[0].cmd('xterm -hold -geometry 130x40+0+900 -e python3 start_node.py %s %d &' %(LOCALHOST,BOOT_PORT))

    boot_ip = hosts[0].IP()

    # rest of the nodes
    port = BOOT_PORT+1
    for host in hosts[1:]:
        # time.sleep(1)
        # cmd = 'xterm -hold -geometry 130x40+0+900 -e python3 -u start_node.py %s %d %s %d &' %(LOCALHOST,port,boot_ip,BOOT_PORT)
        # print cmd
        # print boot_ip
        host.cmd('xterm -hold -geometry 130x40+0+900 -e python3 -u start_node.py %s %d %s %d &' %(LOCALHOST,port,boot_ip,BOOT_PORT))
        port+=1

    raw_input('Press enter to stop all nodes.')
    net.stop()

if __name__ == '__main__':
    # Tell mininet to print useful information
    setLogLevel('info')
    test()