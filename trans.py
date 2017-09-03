import time


class Ledger(object):

    """
    A bitcoin-like ledger - containing a list of transactions.

    Contains a "genesis transaction" that each node is aware of.
    """

    def __init__(self, node_id):
        self.node_id = node_id  # belong to which node
        # Genesis Transaction
        self.record = [Transaction(None, node_id, None, 100, None)]

    # TODO: Support adding a list of transactions (list.extend)
    def add_tx(self, tx):
        if tx not in self.record:
            self.record.append(tx)
            self.record.sort(key=lambda tx: tx.tx_id)

    def gen_trans(self, sender, receiver, witness, amount):
        """
        Generate a new transaction (or a pair of them.)

        This may fail if the sender doesn't have sufficient balance.
        """

        sender_balance = 0
        input_txs = []

        for tx in self.record:

            # Find unspent transactions owned by the sender
            if not tx.spent and tx.receiver == sender:
                sender_balance += tx.amount
                input_txs.append(tx)

            # Found transactions with enough balance?
            if sender_balance >= amount:
                break

        # Could not find sufficient inputs
        # (Sender doesn't have enough balance)
        if sender_balance < amount:
            return False, []

        txs = []

        # Add a transaction from sender to receiver
        txs.append(Transaction(sender, receiver, witness, amount,
                               input_tx=input_txs))

        # When sender has more than enough balance - we credit the rest back to them
        if sender_balance > amount:
            txs.append(Transaction(sender, sender, witness, sender_balance - amount,
                                   input_tx=input_txs))

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
    tx1 = Transaction(None, "a", "a", 100, None)
    l = Ledger("a")
    tx2 = Transaction(None, "a", "a", 100, None)
    l.add_tx(tx2)
    l.add_tx(tx1)
    txs = [Transaction("a","b","c",50, [tx1]), Transaction("b","a","c",50, [tx1])]
    print(l.verify_trans(txs))
