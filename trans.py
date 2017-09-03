from utils import random_id
import time


class Ledger(object):

    """
    A bitcoin-like ledger - containing a list of transactions.

    Contains a "genesis transaction" that each node is aware of.
    """

    def __init__(self, node_id):
        self.node_id = node_id  # belong to which node
        self.record = [Transaction(None, node_id, None, 100, None)]  # Genesis Transaction

    def add_tx(self, tx):
        if tx not in self.record:
            self.record.append(tx)
            self.record.sort(key=lambda tx: tx.tx_id)

    def gen_trans(self, sender, receiver, witness, amount):
        money = 0
        input_tx = []
        txs = []
        for trans in self.record:
            if not trans.spent and trans.receiver == sender:
                money += trans.amount
                input_tx.append(trans)
            if money >= amount:
                break
        if money < amount:
            return False, txs
        txs.append(Transaction(sender, receiver, witness, amount, input_tx=input_tx))
        if money > amount:
            txs.append(Transaction(sender, sender, witness, money - amount, input_tx=input_tx))
        return True, txs

    def verify_trans(self, txs):
        if((len(txs) == 2 and
                txs[0].input_tx == txs[1].input_tx and
                txs[0].sender == txs[1].sender and
                txs[0].witness == txs[1].witness) or
                len(txs) == 1):
            input_tx = txs[0].input_tx
            sender = txs[0].sender
            money = 0
            
            for tx in input_tx:
                if tx not in self.record or tx.receiver != sender or self.record[self.record.index(tx)].spent:
                    return False
                else:
                    money += tx.amount

            if money != txs[0].amount + (txs[1].amount if len(txs) == 2 else 0):
                return False
            return True
        else:
            return False

    def __iter__(self):
        return iter(self.record)

    def __repr__(self):
        r = ""
        for _ in self.record:
            r += (repr(_) + "\n")
        return r


class Transaction(object):

    def __init__(self, sender, receiver, witness, amount, input_tx=None):

        self.tx_id = time.time() * (10**9)  # transaction id is time(for virtual synchrony) multiplying 10^9 it to get time in nanoseconds
        self.input_tx = input_tx  # input transactions, None for Genesis
        self.sender = sender
        self.receiver = receiver
        self.witness = witness
        self.amount = amount
        self.spent = False

    def __eq__(self, other):
        return self.tx_id == other.tx_id  # no need to compare other attributes id must be unique

    def __repr__(self):
        return "%r %r %r %r %r" % (repr(int(self.tx_id)), repr(self.sender), repr(self.receiver), repr(self.amount), repr(self.spent))


if __name__ == '__main__':
    tx1 = Transaction(None, "third", None, None, 100)
    l = Ledger("second")
    tx2 = Transaction(None, "first", None, None, 100)
    l.add_trans(tx2)
    l.add_trans(tx1)
    print(l)
