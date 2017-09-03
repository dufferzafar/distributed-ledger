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

    def __iter__(self):
        return iter(self.record)

    def __repr__(self):
        r = ""
        for _ in self.record:
            r += (repr(_) + "\n")
        return r

    def __getitem__(self, idx):
        return self.record[idx]

    def index(self, item):
        return self.record.index(item)

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

        # When a sender has more than enough balance
        # We credit the rest back to them. (Just like bitcoin does.)
        if sender_balance > amount:
            txs.append(Transaction(sender, sender, witness, sender_balance - amount,
                                   input_tx=input_txs))

        return True, txs

    def verify_trans(self, txs):
        """
        Verify that a transaction (pair) is valid wrt the ledger.
        """

        # If the tranasction is a pair - both of them should have same fields
        if(len(txs) == 1) or (len(txs) == 2 and
                              txs[0].input_tx == txs[1].input_tx and
                              txs[0].sender == txs[1].sender and
                              txs[0].witness == txs[1].witness):

            input_amount = 0

            # Check whether all input transactions are correctly valid
            for tx in txs[0].input_tx:

                if (
                    # An input may be invalid because
                    tx not in self.record or  # It may be Unknown
                    # It may not be owned by the sender
                    tx.receiver != txs[0].sender or
                    # It may be already spent
                    self.record[self.record.index(tx)].spent
                ):
                    return False
                else:
                    input_amount += tx.amount

            # Sum of inputs should match the sum of outputs
            # TODO: This could be replaced by sum() by adding an __radd__
            # method to the transaction class
            output_amount = txs[0].amount + (txs[1].amount if len(txs) == 2 else 0)
            if input_amount != output_amount:
                return False

            return True

        else:
            return False


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
