import asyncio
import logging
import os
import sys
import signal
import config
import re  # regex

from kademlia_dht import Node
from aioconsole import ainput
from start_node import setup_logging


async def cli(node):

    while True:
        cmd = await ainput(">>> ")
        cmd = cmd.strip()  # because reads the "\n" when you press enter

        if len(cmd) == 0:
            continue
        # can the commands and arguments be handled in a better way?
        args = re.findall(r'"([^"]*)"', cmd)  # listing all arguments (must be each double quotes)
        cmd = cmd.split()[0]

        if cmd == 'dht':
            print(node)

        elif cmd == 'routing_table':
            print(node.routing_table)

        elif cmd == 'put':
            if (len(args) != 2):
                print("Expected 2 arguments, %d given" % len(args))
            else:
                await node.put(args[0], args[1], False)

        elif 'get' in cmd:
            if (len(args) != 1):
                print("Expected 1 argument, %d given" % len(args))
            try:
                value = await node.get(args[0], False)
                print(value)
            except KeyError:
                print("Key not found")

        else:
            print("Please enter valid input.\nType help to see commands")
        # TODO implement rest of the functions and help


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
