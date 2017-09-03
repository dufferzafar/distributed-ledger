import asyncio
import logging
import socket
import pickle

from functools import wraps

from routing_table import RoutingTable
from utils import sha1_int, random_id, gen_pub_pvt, verify_msg
from datagram_rpc import DatagramRPCProtocol

from transaction import Ledger

logger = logging.getLogger(__name__)


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


class Node(DatagramRPCProtocol):

    def __init__(self, alpha=3, k=20, identifier=None):

        # Generate public private key pair
        self.pub_key, self.pvt_key = gen_pub_pvt()

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
        self.routing_table = RoutingTable(self.identifier, k=k)

        # Am I busy handling some transaction? (Status, Transaction)
        self.isbusy = (False, None)

        # A list of message_ids that I've broadcasted
        # (required to stop infinite flooding)
        # TODO: Move this to DatagramRPCProtocol?
        self.broadcast_list = []

        # My list of transactions
        self.ledger = Ledger(self.identifier)

        super(Node, self).__init__()

    def storage_str(self):
        dht = ""
        for k, v in self.storage.items():
            dht += "%d : %r\n" % (k, v)
        return dht

    def broadcast_received(self, peer, message_identifier, procedure_name, *args):
        peer_identifier = args[0]
        self.routing_table.update_peer(peer_identifier, peer)  # update the routing table

        # TODO: Move this to DatagramRPCProtocol?
        if message_identifier not in self.broadcast_list:  # if message identifier is not in list
            self.broadcast_list.append(message_identifier)  # append it to broadcast list
            self.broadcast(message_identifier, procedure_name, *args)  # broadcast it to other peers
            super(Node, self).broadcast_received(peer, message_identifier, procedure_name, *args)  # call super's broadcast received that will call the procedure_name
        else:
            # BUG: This should get printed atleast once (but doesn't?)
            print("Old Message")

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
    def send_bitcoins(self, peer_sock, peer_id, receiver_id, witness_id, amount):
        # This node is the sender
        # Caller is the node that initiated the call (can be sender itself or cli.py)

        trans_ok, txs = self.ledger.gen_trans(self.identifier, receiver_id, witness_id, amount)

        response = ""
        if not trans_ok:
            response = "Not enough balance"
        elif self.isbusy[0]:
            response = "Node already busy in another tx %d" % (self.isbusy[1][0].id)
        else:
            self.isbusy = (True, txs)
            response = "Initiating two phase commit Protocol from %d to %d using %d as witness." % (self.identifier, receiver_id, witness_id)

        return (self.identifier, response)

    @remote
    def become_receiver(self, peer_sock, peer_id, txs):
        logger.info("Handling request to become receiver for the transactions %r", txs)

        if self.isbusy[0] and self.isbusy[1] != txs:
            logger.info("Cannot become receiver already busy in another transaction")
            return (self.identifier, "busy")  # return busy
        else:
            # TODO: Perform validation of the transaction
            logger.info("Became receiver for the transactions %r", txs)

            # I'm now busy handling this tx
            self.isbusy = (True, txs)
            return (self.identifier, "yes")  # return yes

    @remote
    def become_witness(self, peer_sock, peer_id, txs):
        logger.info("Handling request to become receiver for the transaction %r", txs)
        if self.isbusy[0] and self.isbusy[1] != txs:  # check if node busy in other trans
            logger.info("Cannot become witness already busy in another tranasction")
            return (self.identifier, "busy")  # return busy
        else:
            # TODO: Perform validation of the transaction
            logger.info("Became witness for the transaction %r", txs)

            # I'm now busy handling this tx
            self.isbusy = (True, txs)
            return (self.identifier, "yes")  # return yes

    @remote
    def get_ledger(self, peer_sock, peer_id):
        return (self.identifier, self.ledger)

    @remote
    def print_ledger(self, peer_sock, peer_id):
        print(self.ledger)
        return (self.identifier, True)

    @remote
    def add_tx_to_ledger(self, peer, peer_id, tx):
        self.ledger.add_tx(tx)
        logger.info("Added transaction %d to the ledger", tx.id)
        return (self.identifier, True)

    @remote
    def commit_tx(self, peer, peer_id, txs, digital_signature, pub_key, *args):

        logger.info("Verifying Digital Signature %r", txs)
        signature_matches = verify_msg(pub_key, repr(txs), digital_signature)

        if signature_matches:
            logger.info("Digital Signature verification successfull")
            tx_type = "new"

            # Transaction already in ledger
            if(txs[0] in self.ledger.record):
                tx_type = "old"

            # Is someone trying to game the system?
            if(tx_type == "old" and len(txs) == 2 and txs[1] not in self.ledger.record):
                tx_type = "weird"

            if tx_type == "new":
                logger.info("Verifying Transaction %r", txs)

                if self.ledger.verify_trans(txs):
                    logger.info("Transaction successfully verified")

                    # Mark each of the inputs as spent
                    for tx in txs[0].input_tx:
                        self.ledger[self.ledger.index(tx)].spent = True

                    # Add theses transactions to my ledger
                    for tx in txs:
                        self.ledger.add_tx(tx)
                        logger.info("Added transaction %d to the ledger", tx.id)

                    logger.info("Transaction successfully committed %r", txs)

                    # I am now free from handling this transaction
                    if(self.identifier in [txs[0].sender, txs[0].receiver, txs[0].witness]):
                        self.isbusy = (False, None)

                    return (self.identifier, "committed")
                else:
                    # TODO: Print the reason it failed too?
                    logger.warn("Transaction verification failed")

                    return (self.identifier, "abort")

            elif tx_type == "old":
                logger.info("Transaction already in Ledger")
                return (self.identifier, "committed")

            else:
                logger.info("Weird transaction %d", tx[0].id)
                return (self.identifier, "abort")
        else:
            logger.info("Digital Signature Verification Failed!")
            return (self.identifier, "abort")

    @remote
    def abort_tx(self, peer, peer_id, txs):

        for tx in txs:
            if tx in self.ledger.record:
                self.ledger.record.remove(tx)

        # TODO: Revert the 'spent' field of input transactions
        # (but only if it was changed)
        # This requires some kind of an undo log

        if self.isbusy[0] and self.isbusy[1] == txs:
            self.isbusy = (False, None)
            logger.info("Transaction %r aborted!", txs)

            return (self.identifier, "aborted")

        return (self.identifier, "Not involved in this transaction")

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
