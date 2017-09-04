import logging

from kademlia_node import KademliaNode, rpc
from utils import gen_pub_pvt, verify_msg

from transaction import Ledger

logger = logging.getLogger(__name__)


class Node(KademliaNode):

    def __init__(self):

        # Initialize KademliaNode
        super(Node, self).__init__()

        # Generate public private key pair
        self.pub_key, self.pvt_key = gen_pub_pvt()

        # Am I busy handling some transaction? (Status, Transaction)
        self.isbusy = (False, None)

        # A list of message_ids that I've broadcasted
        # (required to stop infinite flooding)
        # TODO: Move this to DatagramRPCProtocol?
        self.broadcast_list = []

        # My list of transactions
        self.ledger = Ledger(self.identifier)

        # These are used by DatagramRPCProtocol
        self.reply_functions = self.find_reply_functions()

    def find_reply_functions(self):
        funcs = []
        funcs.extend(Node.__dict__.values())
        funcs.extend(KademliaNode.__dict__.values())

        return {
            func.remote_name: func.reply_function
            for func in funcs if hasattr(func, 'remote_name')
        }

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

    def request_received(self, peer, message_identifier, procedure_name, args, kwargs):
        peer_identifier = args[0]
        self.routing_table.update_peer(peer_identifier, peer)

        super(Node, self).request_received(peer, message_identifier, procedure_name, args, kwargs)

    def reply_received(self, peer, message_identifier, response):
        peer_identifier, response = response
        self.routing_table.update_peer(peer_identifier, peer)

        super(Node, self).reply_received(peer, message_identifier, response)

    @rpc
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

    @rpc
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

    @rpc
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

    @rpc
    def get_ledger(self, peer_sock, peer_id):
        return (self.identifier, self.ledger)

    @rpc
    def print_ledger(self, peer_sock, peer_id):
        print(self.ledger)
        return (self.identifier, True)

    @rpc
    def add_tx_to_ledger(self, peer, peer_id, tx):
        self.ledger.add_tx(tx)
        logger.info("Added transaction %r to the ledger", tx)
        return (self.identifier, True)

    @rpc
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

    @rpc
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
