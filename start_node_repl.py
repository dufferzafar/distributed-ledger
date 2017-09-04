import asyncio
import signal
import sys
import shlex
import socket

# TODO: Is cmd module made async a better alternative?
# https://pymotw.com/2/cmd/index.html#module-cmd
# https://stackoverflow.com/questions/37866403
from aioconsole import ainput

from node import Node
from start_node import two_phase_protocol, setup_logging

from utils import random_id
from node_repl_utils import get_sock_from_name, generate_help_dict

HELP_DICT = generate_help_dict()

async def node_repl(node):

    while True:

        line = await ainput(">>> ")

        # Since it reads the "\n" when you press enter
        line = line.strip()

        if not line:
            continue

        # Handle arguments with spaces etc.
        line = list(shlex.shlex(line))

        cmd = line[0]
        args = line[1:]

        if cmd in ['id']:
            "Print id of a node"

            if len(args) == 1:
                peer_name = args[0]
                peer_socket = get_sock_from_name(args[0])
                try:
                    peer_id = await node.ping(peer_socket, node.identifier)
                    print("%s's id is %d" % (peer_name, peer_id))
                except socket.timeout:
                    print("Failed to ping node %s" % args[0])
            else:
                print("My id is %d" % node.identifier)

        # TODO: Print hash table of a particular node
        elif cmd in ['ht', 'hash_table']:
            "Print my hash table"

            print(node.storage_str())

        # TODO: Print routing table of a particular node
        elif cmd in ['rt', 'routing_table']:
            "Print my routing table"

            print(node.routing_table)

        elif cmd in ['put']:
            "Store a (key, value) pair on the network DHT"

            if (len(args) != 2):
                print("Expected 2 arguments, %d given" % len(args))
            else:
                num = await node.put(args[0], args[1], hashed=False)
                print("Value stored at %d node(s)" % num)

        elif cmd in ['get']:
            "Access a previously stored value by its key"

            if (len(args) != 1):
                print("Expected 1 argument, %d given" % len(args))
            else:
                try:
                    value = await node.get(args[0], hashed=False)
                    print(value)
                except KeyError:
                    print("Key not found")

        elif cmd in ['send_bitcoins']:
            "Send bitcoins to a node"

            if (len(args) != 4):
                print("Expected 4 arguments, %d given" % len(args))
            else:
                try:
                    sender_sock = get_sock_from_name(args[0])
                    receiver_sock = get_sock_from_name(args[1])
                    witness_sock = get_sock_from_name(args[2])

                    receiver_id = await node.ping(receiver_sock, node.identifier)
                    witness_id = await node.ping(witness_sock, node.identifier)
                    amount = int(args[3])

                    reply = await node.request(sender_sock, "send_bitcoins", node.identifier, int(receiver_id), int(witness_id), amount)
                    print(reply)

                except Exception as e:
                    print("Exception Caught : ", e)

        elif cmd in ['?', 'help']:
            "List commands"

            # Find left-justification factor
            ljust = max(map(len, HELP_DICT.keys()))
            for cmd, doc in HELP_DICT.items():
                print(cmd.ljust(ljust) + " : " + doc)

            print()

        elif cmd in ['bd', 'brd', 'bc', 'broadcast']:
            "Broadcast an RPC over the network"

            if (len(args) < 1):
                print("Expected atleast 1 argument, %d given" % len(args))
            else:
                await node.broadcast(random_id(), args[0], node.identifier, *args[1:])

        elif cmd in ['ld', 'ledger']:
            "Pretty print the ledger."

            print(node.ledger)

        else:
            print("Please enter valid input.\nType help to see commands")


def start_node_with_repl(sock_addr):

    loop = asyncio.get_event_loop()

    # On receiving SIGINT Ctrl+C it will try to stop the loop
    loop.add_signal_handler(signal.SIGINT, loop.stop)

    f = loop.create_datagram_endpoint(Node, local_addr=sock_addr)
    _, node = loop.run_until_complete(f)
    setup_logging("cli", to_file=True)
    print("MyId :", node.identifier)

    node.socket_addr = node.transport.get_extra_info('sockname')

    loop.run_until_complete(node.store(node.socket_addr, node.identifier, node.identifier, (node.socket_addr, node.pub_key)))  # store my pub_key in my dht
    loop.create_task(two_phase_protocol(node))
    loop.create_task(node_repl(node))
    loop.run_forever()


if __name__ == '__main__':
    # TODO: Improved argument parsing via docopt or click
    start_node_with_repl(
        sock_addr=(sys.argv[1], int(sys.argv[2]))
    )
