import asyncio
import logging
import os
import sys

import config

from kademlia import KademliaNode


def setup_logging(node_id):

    if not os.path.exists(config.LOG_DIR):
        os.mkdir(config.LOG_DIR)

    kademlia_logger = logging.getLogger('kademlia')
    kademlia_logger.setLevel(logging.DEBUG)

    stream_handler = logging.StreamHandler()
    # stream_handler = logging.FileHandler('logs/%d.log' % node_id, "w")
    stream_handler.setLevel(logging.DEBUG)

    format_ = logging.Formatter('%(asctime)s - %(message)s')
    stream_handler.setFormatter(format_)

    kademlia_logger.addHandler(stream_handler)


def start_a_node(sock_addr, bootstrap_addr=None):

    # DEBUG:
    print(sock_addr[0], sock_addr[1])

    loop = asyncio.get_event_loop()

    f = loop.create_datagram_endpoint(KademliaNode, local_addr=sock_addr)
    _, node = loop.run_until_complete(f)

    # Setup logging once we have the ID
    setup_logging(node.identifier)

    print(node.identifier)

    # TODO: Will this work? Test!
    if bootstrap_addr:
        loop.run_until_complete(node.ping(bootstrap_addr, node.identifier))

    loop.run_forever()


if __name__ == '__main__':

    # TODO: Improved argument parsing via docopt or click

    if len(sys.argv) == 5:
        start_a_node(
            sock_addr=(sys.argv[1], int(sys.argv[2])),
            bootstrap_addr=(sys.argv[3], int(sys.argv[4]))
        )
    else:
        start_a_node(
            sock_addr=(sys.argv[1], int(sys.argv[2]))
        )
