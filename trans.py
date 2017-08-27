from utils import random_id
import time


class Ledger(object):

    """
    A bitcoin-like ledger - containing a list of transactions.

    Contains a "genesis transaction" that each node is aware of.
    """

    def __init__(self, node_id):
        self.node_id = node_id  # belong to which node
        self.ledger = [Transaction(None, node_id, None, None, 100)]  # Genesis Transaction

    def add_trans(self, tx):
        self.ledger.append(tx)
        self.ledger.sort(key=lambda tx: tx.tx_id)

    def verify_trans(self, tx):
        pass
        # TODO method to verify a transaction based on existing ledger

    def __iter__(self):
        return iter(self.ledger)

    def __repr__(self):
        r = ""
        for _ in self.ledger:
            r += (repr(_) + "\n")
        return r


class Transaction(object):

    def __init__(self, sender, receiver, witness, amount, input_tx=None):

        self.tx_id = time.time()  # transaction id is time(for virtual synchrony)
        self.input_tx = input_tx  # input transactions, None for Genesis
        self.sender = sender
        self.receiver = receiver
        self.witness = witness
        self.amount = amount
        self.spent = False

    def __eq__(self, other):
        return self.tx_id == other.tx_id  # no need to compare other attributes id must be unique

    def __repr__(self):
        return "%r %r %r" % (repr(self.tx_id), repr(self.sender), repr(self.receiver))


if __name__ == '__main__':
    tx1 = Transaction(None, "third", None, None, 100)
    l = Ledger("second")
    tx2 = Transaction(None, "first", None, None, 100)
    l.add_trans(tx2)
    l.add_trans(tx1)
    print(l)
