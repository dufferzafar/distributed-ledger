import asyncio
import re
import signal
import sys

# TODO: Is cmd module made async a better alternative?
# https://pymotw.com/2/cmd/index.html#module-cmd
# https://stackoverflow.com/questions/37866403
from aioconsole import ainput

from node import Node
from start_node import handle_trans
from repl import REPL


async def start_repl(node):

    repl = REPL(node)

    while True:

        cmd = await ainput(">>> ")

        # Since it reads the "\n" when you press enter
        cmd = cmd.strip()

        if not cmd:
            continue

        # Listing all arguments (must be each double quotes)

        # TODO: Use shlex for better parsing?
        # https://pymotw.com/2/shlex/
        args = re.findall(r'"([^"]*)"', cmd)
        cmd = cmd.split()[0]

        repl.exec_cmd(cmd, args)

        # TODO: Implement rest of the functions and help

        # TODO: Handle socket exceptions


def start_node_with_cli(sock_addr):

    loop = asyncio.get_event_loop()

    # On receiving SIGINT Ctrl+C it will try to stop the loop
    loop.add_signal_handler(signal.SIGINT, loop.stop)

    f = loop.create_datagram_endpoint(Node, local_addr=sock_addr)
    _, node = loop.run_until_complete(f)

    print("My ID :", node.identifier)

    node.socket_addr = node.transport.get_extra_info('sockname')

    # Store my pub_key in the dht
    # BUG: Should this be a put?
    loop.run_until_complete(node.store(node.socket_addr, node.identifier, node.identifier, (node.socket_addr, node.pub_key)))

    loop.create_task(handle_trans(node))

    loop.create_task(start_repl(node))

    loop.run_forever()


if __name__ == '__main__':
    # TODO: Improved argument parsing via docopt or click
    start_node_with_cli(
        sock_addr=(sys.argv[1], int(sys.argv[2]))
    )
