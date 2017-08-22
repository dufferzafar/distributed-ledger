import sys
import asyncio

from kademlia import KademliaNode


def start_a_node(sock_addr, bootstrap_addr=None):

    loop = asyncio.get_event_loop()

    f = loop.create_datagram_endpoint(KademliaNode, local_addr=sock_addr)
    _, node = loop.run_until_complete(f)

    # TODO: Will this work? Test!
    if bootstrap_addr:
        loop.run_until_complete(node.ping(bootstrap_addr, node.identifier))

    loop.run_forever()


if __name__ == '__main__':

    start_a_node(
        # TODO: Improved argument parsing via docopt or click
        sock_addr=(sys.argv[1], int(sys.argv[2]))
    )
