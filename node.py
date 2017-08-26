import asyncio
import logging
import socket

from functools import wraps

from routing_table import RoutingTable
from utils import sha1_int, random_id, gen_pub_pvt
from datagram_rpc import DatagramRPCProtocol

logger = logging.getLogger(__name__)


def remote(func):
    """
    A decorator used to indicate an RPC.

    All @remote procedures return a 2-tuple: (node_identifier, response)

    The node_identifier is consumed by kademlia to update its tables,
    while the response is sent as a reply back to the caller.
    """
    @asyncio.coroutine
    @wraps(func)
    def inner(*args, **kwargs):
        instance, peer, *args = args
        response = yield from instance.request(peer, inner.remote_name, *args, **kwargs)
        return response

    # string: name of function
    inner.remote_name = func.__name__

    # callable: function object
    inner.reply_function = func

    return inner


class Node(DatagramRPCProtocol):

    def __init__(self, alpha=3, k=20, identifier=None):

        # TODO: Make the node id a function of node's public key
        # Just like Bitcoin wallet IDs use HASH160
        if identifier is None:
            identifier = random_id()

        self.identifier = identifier

        self.routing_table = RoutingTable(self.identifier, k=k)

        # Constants from the kademlia protocol
        self.k = k
        self.alpha = alpha

        # Each node has their own dictionary
        self.storage = {}

        # (Status, TransactionId)
        self.is_busy_in_tx = (False, None)

        super(Node, self).__init__()

    # TODO: This method should ideally be called dht()
    def __str__(self):
        dht = ""
        for k, v in self.storage.items():
            dht += "%d : %r\n" % (k, v)
        return dht

    def request_received(self, peer, message_identifier, procedure_name, args, kwargs):
        peer_identifier = args[0]
        self.routing_table.update_peer(peer_identifier, peer)

        super(Node, self).request_received(peer, message_identifier, procedure_name, args, kwargs)

    def reply_received(self, peer, message_identifier, response):
        peer_identifier, response = response
        self.routing_table.update_peer(peer_identifier, peer)

        super(Node, self).reply_received(peer, message_identifier, response)

    @remote
    def ping(self, peer, peer_identifier):
        logger.info('handling ping(%r, %r)', peer, peer_identifier)

        # The 1st identifier is consumed by kademlia
        # While the 2nd is sent as a reply back to the caller
        return (self.identifier, self.identifier)

    @remote
    def store(self, peer, peer_identifier, key, value):
        logger.info('handling store(%r, %r, %r, %r)',
                    peer, peer_identifier, key, value)

        self.storage[key] = value
        return (self.identifier, True)

    @remote
    def find_node(self, peer, peer_identifier, key):
        logger.info('handling find_node(%r, %r, %r)',
                    peer, peer_identifier, key)

        response = self.routing_table.find_closest_peers(key, excluding=peer_identifier)
        return (self.identifier, response)

    @remote
    def find_value(self, peer, peer_identifier, key):
        logger.info('handling find_value(%r, %r, %r)',
                    peer, peer_identifier, key)

        if key in self.storage:
            response = ('found', self.storage[key])
            return (self.identifier, response)

        response = ('notfound', self.routing_table.find_closest_peers(key, excluding=peer_identifier))
        return (self.identifier, response)

    @remote
    def sendmoney(self, caller, receiver, witness, amount):  # after self, the first argument must always be the caller
        # this node is the sender
        # caller is the node that initiated this can be sender itself or cli.py
        if self.is_busy_in_tx[0]:
            return "Node already busy in another tx %s"

        """ 2 Phase Commit Protocol """
        """ Phase 1 """
        self.is_busy_in_tx = True
        try:
            receiver_sock = self.get(receiver, hashed=True)  # assuming key of reciever is given in hashed
            print("Receiver Found")
        except KeyError:
            self.is_busy_in_tx = False
            return "Reciever not found"

        try:
            witness_sock = self.get(witness, hashed=True)  # assuming key of witness is given in hashed
            print("Witness Found")
        except KeyError:
            self.is_busy_in_tx = False
            return "Witness not found"

        witness_status = yield from self.request(receiver_sock, 'become_witness', self.identifier)
        if witness_status == "busy":
            self.is_busy_in_tx = False
            return "Witness Busy. Transaction Aborted!"
        print("Witness is Ready")

        receiver_status = yield from self.request(receiver_sock, 'become_receiver', self.identifier)
        if receiver_status == "busy":
            self.is_busy_in_tx = False
            return "Receiver Busy. Transaction Aborted!"
        print("Receiver is Ready")

        """ Phase 2"""
        return "Entering Phase 2"

    # TODO Implement become_witness and become_receiver function
    @remote
    def become_receiver(self, sender):
        return "busy"

    @remote
    def become_witness(self, sender):
        return "yes"

    # TODO: Refactor the hashed part
    @asyncio.coroutine
    def put(self, raw_key, value, hashed=True):  # hashed True key being passed is already hashe
        if(not hashed):  # hashed False => key passed needs to be hashed to 160bit
            hashed_key = sha1_int(raw_key)
        else:
            hashed_key = raw_key  # dht key is node_id already hashed

        peers_close_to_key = yield from self.lookup_node(hashed_key, find_value=False)

        store_tasks = [
            self.store(peer, self.identifier, hashed_key, value)
            for _, peer in peers_close_to_key
        ]

        results = yield from asyncio.gather(*store_tasks, return_exceptions=True)
        successful = [r for r in results if r is True]

        return len(successful)

    @asyncio.coroutine
    def get(self, raw_key, hashed=True):  # hashed True key being passed is already hashe
        if(not hashed):  # hashed False => key passed needs to be hashed to 160bit
            hashed_key = sha1_int(raw_key)
        else:
            hashed_key = raw_key

        if hashed_key in self.storage:
            return self.storage[hashed_key]
        try:
            response = yield from self.lookup_node(hashed_key, find_value=True)
        except KeyError as e:
            raise e

        return response

    @asyncio.coroutine
    def lookup_node(self, hashed_key, find_value=False):
        def distance(peer): return peer[0] ^ hashed_key

        contacted, dead = set(), set()

        peers = {
            (peer_identifier, peer)
            for peer_identifier, peer in
            self.routing_table.find_closest_peers(hashed_key)
        }

        if not peers:
            raise KeyError(hashed_key, 'No peers available.')

        while True:
            uncontacted = peers - contacted

            if not uncontacted:
                break

            closest = sorted(uncontacted, key=distance)[:self.alpha]

            for peer_identifier, peer in closest:

                contacted.add((peer_identifier, peer))

                try:
                    if find_value:
                        result, contacts = yield from self.find_value(peer, self.identifier, hashed_key)
                        if result == 'found':
                            return contacts
                    else:
                        contacts = yield from self.find_node(peer, self.identifier, hashed_key)

                except socket.timeout:
                    self.routing_table.forget_peer(peer_identifier)
                    dead.add((peer_identifier, peer))
                    continue

                for new_peer_identifier, new_peer in contacts:
                    if new_peer_identifier == self.identifier:
                        continue
                    peers.add((new_peer_identifier, new_peer))

        if find_value:
            raise KeyError(hashed_key, 'Not found among any available peers.')
        else:
            return sorted(peers - dead, key=distance)[:self.k]

    @asyncio.coroutine
    def ping_all_neighbors(self):
        for node_id, peer in list(self.routing_table):
            yield from self.ping(peer, self.identifier)

    @asyncio.coroutine
    def join(self):
        # http://xlattice.sourceforge.net/components/protocol/kademlia/specs.html#join
        yield from self.lookup_node(self.identifier)
        yield from self.ping_all_neighbors()

        try:
            yield from self.get(self.identifier)
            # search if my public key already in network
        except KeyError:  # key not found
            # TODO: This should ideally be in __init__
            pub_key, pvt_key = gen_pub_pvt()
            # generate public private key pair
            self.pvt_key = pvt_key
            my_sock_addr = self.transport.get_extra_info('sockname')
            # function to get my own socket
            yield from self.put(self.identifier, (my_sock_addr, pub_key))
