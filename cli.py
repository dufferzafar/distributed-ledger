import asyncio
import re
import signal
import socket
import sys

import config

from node import Node

# TODO: Is cmd module made async a better alternative?
# https://pymotw.com/2/cmd/index.html#module-cmd
# https://stackoverflow.com/questions/37866403
from aioconsole import ainput

# A UDP Socket used for interaction with the Mininet Control Server
MN_SOCK = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, 0)
MN_SOCK.bind(("127.0.0.1", 0))


async def cli(node):

    while True:

        cmd = await ainput(">>> ")

        # Since it reads the "\n" when you press enter
        cmd = cmd.strip()

        if not cmd:
            continue

        # TODO: Use shlex for better parsing?
        # https://pymotw.com/2/shlex/

        # Listing all arguments (must be each double quotes)
        args = re.findall(r'"([^"]*)"', cmd)
        cmd = cmd.split()[0]

        if cmd == 'id':
            if len(args) == 2:
                peer_socket = (args[0], int(args[1]))
                peer_id = await node.request(peer_socket, "ping", node.identifier)
                print(peer_id)
            else:
                print(node.identifier)

        elif cmd == 'dht':
            print(node)

        elif cmd == 'routing_table':
            print(node.routing_table)

        elif cmd == 'put':
            if (len(args) != 2):
                print("Expected 2 arguments, %d given" % len(args))
            else:
                await node.put(args[0], args[1], hashed=False)

        elif cmd == 'get':

            if (len(args) != 1):
                print("Expected 1 argument, %d given" % len(args))

            try:
                value = await node.get(args[0], hashed=False)
                print(value)
            except KeyError:
                print("Key not found")
        elif cmd == 'send_money':

            try:
                send_sock = await node.get(int(args[0]), hashed=True)
                print(send_sock)
                reply = await node.request(send_sock, "send_money", node.identifier, int(args[1]), int(args[2]), args[3])
                print(reply)

            except KeyError:
                print("Key not found")

        elif cmd == 'help':
            print("Haven't implemented yet")

        elif cmd == 'stop_network':
            status = MN_SOCK.sendto(b"stop", config.MN_CONTROLLER_SOCKET)
            print(status)

        else:
            print("Please enter valid input.\nType help to see commands")

        # TODO: Implement rest of the functions and help

        # TODO: Handle socket exceptions


def start_node_with_cli(sock_addr):

    loop = asyncio.get_event_loop()

    # On receiving SIGINT Ctrl+C it will try to stop the loop
    loop.add_signal_handler(signal.SIGINT, loop.stop)

    f = loop.create_datagram_endpoint(Node, local_addr=sock_addr)
    _, node = loop.run_until_complete(f)

    print("MyId :", node.identifier)

    loop.create_task(cli(node))
    loop.run_forever()


if __name__ == '__main__':
    # TODO: Improved argument parsing via docopt or click
    start_node_with_cli(
        sock_addr=(sys.argv[1], int(sys.argv[2]))
    )
