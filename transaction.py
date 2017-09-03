import time


class Ledger(object):

    """
    A bitcoin-like ledger - containing a list of transactions.

    Contains a "genesis transaction" that each node is aware of.
    """

    def __init__(self, node_id):
        # ID of the Ledger owner
        self.node_id = node_id

        # Genesis Transaction
        self.record = [Transaction.genesis(receiver=node_id)]

    def __iter__(self):
        return iter(self.record)

    def __repr__(self):
        return "Ledger(records=[\n%s\n])" % ",\n".join([repr(tx) for tx in self.record])

    def __getitem__(self, idx):
        return self.record[idx]

    def index(self, item):
        return self.record.index(item)

    # TODO: Support adding a list of transactions (list.extend)
    def add_tx(self, tx):
        if tx not in self.record:
            self.record.append(tx)
            self.record.sort(key=lambda tx: tx.id)

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
            if input_amount != sum(txs):
                return False

            return True

        else:
            return False


class Transaction(object):

    def __init__(self, sender, receiver, witness, amount, input_tx=None):

        # Transaction ID is time (for virtual synchrony)
        # (multiplying by 10^9 gives us nanoseconds)
        self.id = int(time.time() * (10**9))

        # List of input transactions (None for Genesis)
        self.input_tx = input_tx

        self.sender = sender
        self.receiver = receiver
        self.witness = witness
        self.amount = amount

        # A transaction starts as unspent - but will get spent once it becomes
        # the input of some other transaction.
        self.spent = False

    @staticmethod
    def genesis(receiver, amount=100):
        return Transaction(sender=None, receiver=receiver, witness=None, amount=amount, input_tx=None)

    def __eq__(self, other):
        # No need to compare other attributes as the ID must be unique
        return self.id == other.id

    def __add__(self, other):
        return self.amount + other.amount

    def __radd__(self, other):
        """Add two transactions or a transaction and an int."""

        if isinstance(other, int):
            return self.amount + other

        return self.amount + other.amount

    def __repr__(self):
        return ("Transaction(id=%r, sender=%r, receiver=%r, amount=%r, spent=%r)" %
                (self.id, self.sender, self.receiver, self.amount, self.spent))


if __name__ == '__main__':

    l = Ledger("a")

    # Get the genesis transaction of the ledger
    tx1 = l[0]

    txs = [
        Transaction("a", "b", "c", 50, [tx1]),
        Transaction("a", "a", "c", 50, [tx1]),
    ]

    print(l.verify_trans(txs))

    tx2 = Transaction(None, "a", "a", 100, None)
    l.add_tx(tx2)

    # We can now add two transactions
    print(tx1 + tx2)

    # Or sum a list
    print(sum(txs))

    # Or sum the ledger itself
    print(sum(l))

    # Demo Transaction.__repr__
    print(tx1)

    # Demo Ledger.__repr__
    print(l)
