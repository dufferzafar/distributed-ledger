import asyncio
import logging
import os
import sys
import signal

import config

from node import Node
from utils import random_id, sign_msg


def setup_logging(node_id, to_file=False):

    # TODO: Color the loglines based on their type

    if not os.path.exists(config.LOG_DIR):
        os.mkdir(config.LOG_DIR)

    kademlia_logger = logging.getLogger('node')
    kademlia_logger.setLevel(config.LOGLEVEL)

    stream_handler = logging.StreamHandler()
    if to_file:
        stream_handler = logging.FileHandler('logs/%s.log' % node_id, "w")
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
def log_ledger(node, interval=5):
    while True:
        logger = logging.getLogger('node')
        logger.debug("My Ledger:\n" + repr(node.ledger))
        yield from asyncio.sleep(interval)


@asyncio.coroutine
def two_phase_protocol(node):
    logger = logging.getLogger('node')
    while True:
        if(node.isbusy[0]):  # if involved in some transaction
            txs = node.isbusy[1]  # get that transaction

            if txs[0].sender == node.identifier:  # if current node is the sender
                """Phase 1"""
                print("I am sender")

                digital_signature = sign_msg(node.pvt_key, repr(txs))
                logger.info("Generated Digital Signature %r", digital_signature)
                senders_pub_key = (yield from node.get(txs[0].sender))[1]

                receiver_sock = (yield from node.get(txs[0].receiver))[0]
                receiver_status = yield from node.become_receiver(receiver_sock, node.identifier, txs)

                witness_sock = (yield from node.get(txs[0].witness))[0]
                witness_status = yield from node.become_witness(witness_sock, node.identifier, txs)

                if receiver_status == "busy" or witness_status == "busy":
                    logger.info("Phase 1 failed, aborting transaction!")

                    # Send abort to both receiver & witness
                    receiver_abort = yield from node.abort_tx(receiver_sock, node.identifier, txs)
                    witness_abort = yield from node.abort_tx(witness_sock, node.identifier, txs)

                    # If both of them have aborted then I'll abort too
                    if (witness_abort == "aborted" and receiver_abort == "aborted"):
                        yield from node.abort_tx(node.socket_addr, node.identifier, txs)
                else:
                    """ Phase 2 """
                    logger.info("Phase 1 complete - Now entering Phase 2")

                    # Send commit to both receiver & witness
                    receiver_commit = yield from node.commit_tx(receiver_sock, node.identifier, txs, digital_signature, senders_pub_key)
                    witness_commit = yield from node.commit_tx(witness_sock, node.identifier, txs, digital_signature, senders_pub_key)

                    if (witness_commit == "committed" and receiver_commit == "committed"):
                        logger.info("Phase 2 complete")
                        yield from node.commit_tx(node.socket_addr, node.identifier, txs, digital_signature, senders_pub_key)  # Commit transaction
                        yield from node.broadcast(random_id(), 'commit_tx', node.identifier, txs, digital_signature, senders_pub_key)
                        node.isbusy = (False, None)

                    else:
                        receiver_abort = yield from node.abort_tx(receiver_sock, node.identifier, txs)  # send abort to receiver
                        witness_abort = yield from node.abort_tx(witness_sock, node.identifier, txs)  # send abort to witness

                        if (witness_abort == "aborted" and receiver_abort == "aborted"):
                            yield from node.abort_tx(node.socket_addr, node.identifier, txs)  # send abort to itslef(sender)
                # do the work of sender

            elif txs[0].receiver == node.identifier:
                print("I am receiver")
                # do the work of receiver

            # Do the work of witnes
            elif txs[0].witness == node.identifier:
                print("I am witness")

        yield from asyncio.sleep(1)


def start_node(sock_addr, bootstrap_addr=None):

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
    loop.create_task(log_ledger(node, interval=5))
    loop.create_task(two_phase_protocol(node))
    loop.run_forever()


if __name__ == '__main__':

    # TODO: Improved argument parsing via docopt or click

    if len(sys.argv) == 5:
        start_node(
            sock_addr=(sys.argv[1], int(sys.argv[2])),
            bootstrap_addr=(sys.argv[3], int(sys.argv[4]))
        )
    else:
        start_node(
            sock_addr=(sys.argv[1], int(sys.argv[2]))
        )
