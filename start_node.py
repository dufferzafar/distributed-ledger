import asyncio
import logging
import os
import sys
import signal

import config

from node import Node
from trans import Transaction
from utils import random_id


def setup_logging(node_id):

    if not os.path.exists(config.LOG_DIR):
        os.mkdir(config.LOG_DIR)

    kademlia_logger = logging.getLogger('node')
    kademlia_logger.setLevel(config.LOGLEVEL)

    stream_handler = logging.StreamHandler()
    # stream_handler = logging.FileHandler('logs/%d.log' % node_id, "w")
    stream_handler.setLevel(config.LOGLEVEL)

    format_ = logging.Formatter('\n%(asctime)s - %(message)s\n')
    stream_handler.setFormatter(format_)

    kademlia_logger.addHandler(stream_handler)


@asyncio.coroutine
def continuous_ping(node, to, interval=5):
    while True:
        yield from node.ping(to, node.identifier)
        yield from asyncio.sleep(interval)


@asyncio.coroutine
def log_routing_table(node, interval=5):
    while True:
        logger = logging.getLogger('node')
        logger.debug("My Routing Table:\n" + str(node.routing_table))
        yield from asyncio.sleep(interval)


@asyncio.coroutine
def log_dht(node, interval=5):
    while True:
        logger = logging.getLogger('node')
        logger.debug("My Hash Table:\n" + node.storage_str())
        yield from asyncio.sleep(interval)


@asyncio.coroutine
def handle_trans(node):
    while True:
        if(node.isbusy[0]):  # if involved in some transaction
            tx = node.isbusy[1]  # get that transaction

            if tx.sender == node.identifier:  # if current node is the sender
                """Phase 1"""
                print("I am sender")
                receiver_sock = (yield from node.get(tx.receiver))[0]
                receiver_status = yield from node.become_receiver(receiver_sock, node.identifier, tx)
                witness_sock = (yield from node.get(tx.witness))[0]
                witness_status = yield from node.become_witness(witness_sock, node.identifier, tx)

                if receiver_status == "busy" or witness_status == "busy":
                    receiver_abort = yield from node.abort_tx(receiver_sock, node.identifier, tx)  # send abort to receiver
                    witness_abort = yield from node.abort_tx(witness_sock, node.identifier, tx)  # send abort to witness

                    if (witness_abort == "aborted" and receiver_abort == "aborted"):
                        yield from node.abort_tx(node.transport.get_extra_info('sockname'), node.identifier, tx)  # send abort to itslef(sender)
                else:
                    print("Phase 1 Complete. Entering Phase two")
                    """ Phase 2 """
                    receiver_commit = yield from node.commit_tx(receiver_sock, node.identifier, tx)  # send commit to receiver
                    witness_commit = yield from node.commit_tx(witness_sock, node.identifier, tx)  # send commit to receiver

                    if (witness_commit == "committed" and receiver_commit == "committed"):
                        yield from node.commit_tx(node.transport.get_extra_info('sockname'), node.identifier, tx)  # Commit transaction
                        # TODO broadcast
                        node.isbusy = (False,None)
                    else:
                        receiver_abort = yield from node.abort_tx(receiver_sock, node.identifier, tx)  # send abort to receiver
                        witness_abort = yield from node.abort_tx(witness_sock, node.identifier, tx)  # send abort to witness

                        if (witness_abort == "aborted" and receiver_abort == "aborted"):
                            yield from node.abort_tx(node.transport.get_extra_info('sockname'), node.identifier, tx)  # send abort to itslef(sender)
                # do the work of sender

            elif tx.receiver == node.identifier:
                print("I am receiver")
                # do the work of receiver
            elif tx.witness == node.identifier:
                print("I am witness")
                # do the work of witnes
        yield from asyncio.sleep(1)


def start_a_node(sock_addr, bootstrap_addr=None):

    loop = asyncio.get_event_loop()

    # On receiving SIGINT Ctrl+C - try to stop the loop
    loop.add_signal_handler(signal.SIGINT, loop.stop)

    f = loop.create_datagram_endpoint(Node, local_addr=sock_addr)
    _, node = loop.run_until_complete(f)

    # Setup logging once we have the ID
    setup_logging(node.identifier)

    logging.getLogger('node').info('MyId: %s', node.identifier)

    # For nodes that are not bootstrapper
    if bootstrap_addr:
        loop.run_until_complete(node.join(known_node=bootstrap_addr))

    # Log the routing table & dht every two second
    loop.create_task(log_routing_table(node, interval=2))
    loop.create_task(log_dht(node, interval=2))
    loop.create_task(handle_trans(node))
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
