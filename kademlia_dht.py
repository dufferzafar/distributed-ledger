import asyncio
import logging
import socket

from functools import wraps

from routing_table import RoutingTable
from utils import sha1_int, random_id, gen_pub_pvt
from datagram_rpc import DatagramRPCProtocol

logger = logging.getLogger(__name__)


def remote(func):

    @asyncio.coroutine
    @wraps(func)
    def inner(*args, **kwargs):
        instance, peer, *args = args
        answer = yield from instance.request(peer, inner.remote_name, *args, **kwargs)
        return answer

    # String: name of function
    inner.remote_name = func.__name__

    # Callable: function object
    inner.reply_function = func

    return inner


class KademliaNode(DatagramRPCProtocol):

    def __init__(self, alpha=3, k=20, identifier=None):

        # Use HASH160
        if identifier is None:
            identifier = random_id()

        self.identifier = identifier
        self.routing_table = RoutingTable(self.identifier, k=k)
        self.k = k
        self.alpha = alpha
        self.storage = {}

        super(KademliaNode, self).__init__()

    def request_received(self, peer, message_identifier, procedure_name, args, kwargs):
        peer_identifier = args[0]
        self.routing_table.update_peer(peer_identifier, peer)

        super(KademliaNode, self).request_received(peer, message_identifier, procedure_name, args, kwargs)

    def reply_received(self, peer, message_identifier, answer):
        peer_identifier, answer = answer
        self.routing_table.update_peer(peer_identifier, peer)

        super(KademliaNode, self).reply_received(peer, message_identifier, answer)

    @remote
    def ping(self, peer, peer_identifier):
        logger.info('handling ping(%r, %r)', peer, peer_identifier)

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

        return (self.identifier, self.routing_table.find_closest_peers(key, excluding=peer_identifier))

    @remote
    def find_value(self, peer, peer_identifier, key):
        logger.info('handling find_value(%r, %r, %r)',
                    peer, peer_identifier, key)

        if key in self.storage:
            return (self.identifier, ('found', self.storage[key]))
        return (self.identifier, ('notfound', self.routing_table.find_closest_peers(key, excluding=peer_identifier)))

    @asyncio.coroutine
    def put(self, raw_key, value):
        # hashed_key = sha1_int(raw_key) # key is node_id which is already hashed to 160bit
        # why do we need to hash again?
        hashed_key = raw_key; # dht key is node_id already hashed
        peers_close_to_key = yield from self.lookup_node(hashed_key, find_value=False)

        store_tasks = [
            self.store(peer, self.identifier, hashed_key, value)
            for _, peer in peers_close_to_key
        ]

        results = yield from asyncio.gather(*store_tasks, return_exceptions=True)
        successful = [r for r in results if r is True]

        return len(successful)

    @asyncio.coroutine
    def get(self, raw_key):
        # hashed_key = sha1_int(raw_key) # key is node_id which is already hashed to 160bit
        # why do we need to hash again?
        hashed_key = raw_key
        if hashed_key in self.storage:
            return self.storage[hashed_key]
        try:
            answer = yield from self.lookup_node(hashed_key, find_value=True)
        except KeyError as e:
            raise e

        return answer

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
