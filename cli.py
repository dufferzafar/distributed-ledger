import asyncio
import logging
import os
import sys
import signal
import config

from kademlia_dht import Node
from aioconsole import ainput
from start_node import setup_logging


async def cli(node):
    while True:
        line = await ainput(">>> ")
        line = line.strip()  # because reads the "\n" when you press enter
        if line == 'my dht':
            print(node)
        # TODO implement rest of the functions


def start_node_with_cli(sock_addr):

    loop = asyncio.get_event_loop()
    # on receiving SIGINT Ctrl+C it will try to stop the loop
    loop.add_signal_handler(signal.SIGINT, loop.stop)
    f = loop.create_datagram_endpoint(Node, local_addr=sock_addr)
    _, node = loop.run_until_complete(f)

    # Setup logging once we have the ID
    setup_logging(node.identifier)

    logging.getLogger('kademlia').info('MyId: %s', node.identifier)

    # Log the routing table every two second
    # loop.create_task(log_routing_table(node, interval=2))
    # loop.create_task(log_dht(node, interval=2))
    loop.create_task(cli(node))
    loop.run_forever()


if __name__ == '__main__':
    # TODO: Improved argument parsing via docopt or click
    start_node_with_cli(
        sock_addr=(sys.argv[1], int(sys.argv[2]))
    )
