import asyncio
import re
import signal
import sys

from node import Node

# TODO: Is cmd module made async a better alternative?
# https://pymotw.com/2/cmd/index.html#module-cmd
# https://stackoverflow.com/questions/37866403
from aioconsole import ainput
from cli_utils import get_sock_from_name
from start_node import handle_trans
from utils import random_id,sha1_int

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
            if len(args) == 1:
                peer_socket = get_sock_from_name(args[0])
                peer_id = await node.ping(peer_socket, node.identifier)
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
            else:
                try:
                    value = await node.get(args[0], hashed=False)
                    print(value)
                except KeyError:
                    print("Key not found")

        elif cmd == 'send_bitcoins':

            if (len(args) != 4):
                print("Expected 4 arguments, %d given" % len(args))
            else:
                try:
                    sender_sock = get_sock_from_name(args[0])
                    receiver_sock = get_sock_from_name(args[1])
                    witness_sock = get_sock_from_name(args[2])

                    receiver_id = await node.request(receiver_sock, 'ping', node.identifier)
                    witness_id = await node.request(witness_sock, 'ping', node.identifier)
                    amount = int(args[3])

                    reply = await node.request(sender_sock, "send_bitcoins", node.identifier, int(receiver_id), int(witness_id), amount)
                    print(reply)

                except Exception as e:
                    print("Exception Caught : ", e)

        elif cmd == 'help':
            print("Haven't implemented yet")

        elif cmd == 'broadcast':
            node.broadcast(random_id(), 'store', node.identifier, sha1_int("harish"), "chandra")
            # node.broadcast(random_id(), 'ping', node.identifier)

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

    node.socket_addr = node.transport.get_extra_info('sockname')

    loop.run_until_complete(node.store(node.socket_addr, node.identifier, node.identifier, (node.socket_addr, node.pub_key)))  # store my pub_key in my dht
    loop.create_task(handle_trans(node))
    loop.create_task(cli(node))
    loop.run_forever()


if __name__ == '__main__':
    # TODO: Improved argument parsing via docopt or click
    start_node_with_cli(
        sock_addr=(sys.argv[1], int(sys.argv[2]))
    )
