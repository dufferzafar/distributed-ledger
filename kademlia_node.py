import asyncio
import logging
import socket
import pickle

from functools import wraps

from routing_table import RoutingTable
from datagram_rpc import DatagramRPCProtocol
from utils import sha1_int, random_id


logger = logging.getLogger('node')


def remote(func):
    """
    A decorator used to indicate an RPC.

    All @remote procedures if explicitly called via a request message must have node.identifier as the first argument
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


class KademliaNode(DatagramRPCProtocol):

    def __init__(self, alpha=3, k=20, identifier=None):

        # Initialiaze DatagramRPCProtocol
        super(KademliaNode, self).__init__()

        # TODO: Make the node id a function of node's public key
        # Just like Bitcoin wallet IDs use HASH160
        if identifier is None:
            identifier = random_id()

        self.identifier = identifier

        # Constants from the kademlia protocol
        self.k = k
        self.alpha = alpha

        # Each node has their own dictionary
        self.storage = {}

        # The k-bucket based kademlia routing table
        self.routing_table = RoutingTable(self.identifier, k=self.k)

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

    @asyncio.coroutine
    def ping_all_neighbors(self):
        for node_id, peer in list(self.routing_table):
            yield from self.ping(peer, self.identifier)

    @asyncio.coroutine
    def join(self, known_node):
        """
        Run by a node when it wants to join the network.

        http://xlattice.sourceforge.net/components/protocol/kademlia/specs.html#join
        """

        # When a new node is created, ping some known_node
        yield from self.ping(known_node, self.identifier)

        # Try to find all peers close to myself
        # (this'll update my routing table)
        yield from self.lookup_node(self.identifier)

        # Pinging all neighbors will update their routing tables
        yield from self.ping_all_neighbors()

        try:
            # Check if my public key is already in the network
            yield from self.get(self.identifier)
        except KeyError:
            # Store my information onto the network
            # (allowing others to find me)
            yield from self.put(self.identifier, (self.socket_addr, self.pub_key))

            my_genesis_tx = self.ledger.record[0]  # my genesis transaction
            yield from self.add_tx_to_ledger(known_node, self.identifier, my_genesis_tx)  # add it to the ledger of bootstrapper

            ledger_bootstrap = yield from self.get_ledger(known_node, self.identifier)  # get the bootstrapper's ledger

            self.ledger.record = ledger_bootstrap.record  # replace my ledger with that of bootstrappers

            yield from self.broadcast(random_id(), 'add_tx_to_ledger', self.identifier, my_genesis_tx)  # broadcast my genesis transaction to everyone

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
    def broadcast(self, message_identifier, procedure_name, *args, **kwargs):
        """
        Broadcast a message containing a procedure_name to all the nodes
        who will then execute it.

        Arguments:
            message_identifier : unique msg id for each broadcast
            procedure_name : name of the remote procedure to be executed
            args : parameters for that procedure
        """

        logger.info("received a broadcast for procedure %r as message %r", procedure_name, message_identifier)
        if message_identifier not in self.broadcast_list:
            self.broadcast_list.append(message_identifier)

        # Create a mesage with its type, procedure_name and args
        obj = ('broadcast', message_identifier, procedure_name, *args)
        message = pickle.dumps(obj, protocol=0)

        # Send the msg to each connected peer
        for _, peer in self.routing_table:
            self.transport.sendto(message, peer)
