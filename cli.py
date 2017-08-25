import asyncio
import sys
import signal
import re  # regex

from kademlia_dht import Node
from aioconsole import ainput


async def cli(node):

    while True:
        cmd = await ainput(">>> ")
        cmd = cmd.strip()  # because reads the "\n" when you press enter

        if not cmd:  # if empty cmd
            continue
        # can the commands and arguments be handled in a better way?

        # listing all arguments (must be each double quotes)
        args = re.findall(r'"([^"]*)"', cmd)
        cmd = cmd.split()[0]

        if cmd == 'id':  # print my id
            print(node.identifier)

        elif cmd == 'dht':  # print my dht
            print(node)

        elif cmd == 'routing_table':  # print my routing table
            print(node.routing_table)

        elif cmd == 'put':
            if (len(args) != 2):
                print("Expected 2 arguments, %d given" % len(args))
            else:
                await node.put(args[0], args[1], hashed=False)
                # False => key is not already hashed

        elif cmd == 'get':
            if (len(args) != 1):
                print("Expected 1 argument, %d given" % len(args))
            try:
                value = await node.get(args[0], hashed=False)
                # False => key is not already hashed
                print(value)
            except KeyError:
                print("Key not found")

        elif cmd == 'help':
            print("Haven't implemented yet")

        else:
            print("Please enter valid input.\nType help to see commands")
        # TODO implement rest of the functions and help


def start_node_with_cli(sock_addr):

    loop = asyncio.get_event_loop()
    # on receiving SIGINT Ctrl+C it will try to stop the loop
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
