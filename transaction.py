from collections import namedtuple

# TODO: Split ledger/transaction classes into multiple files when code grows.

# TODO: A function that generates 3-4 genesis-like transactions for different nodes?


class Ledger(object):

    """
    A bitcoin-like ledger - containing a list of transactions.

    Contains a "genesis transaction" that each node is aware of.
    """

    def __init__(self):

        # The genesis transaction
        # TODO: Figure this out properly
        TxOut = TxOutput(False, 1000, "")

        Tx = Transaction(
            inputs=[TxOut],
            outputs=[TxOut],
            witness_id="",
        )

        # Each ledger has a genesis transaction.
        self.ledger = [Tx]

    def __iter__(self):
        return self.ledger

    def __repr__(self):
        return repr(self.ledger)


# https://bitcoin.org/en/glossary/output
# https://bitcoin.org/en/developer-guide#transactions
# https://bitcoin.org/en/glossary/unspent-transaction-output
TxOutput = namedtuple(
    "TxOutput",
    [
        # bool: Is this TxOut spent?
        "spent",

        # int: Amount of
        "value",
        "address",
    ]
)


class Transaction(object):

    """
    A bitcoin-like transaction.

    Uses json to convert to/from string.
    """

    def __init__(
            self,

            # The input list of TxOutputs will contain address of sender(s)
            inputs,

            witness_id,

            # The output list of TxOutputs will contain address of receiver(s)
            outputs
    ):

        self.inputs = inputs
        self.witness_id = witness_id
        self.outputs = outputs

    def __repr__(self):
        return repr(self.inputs)


# This code will not be executed when this module is imported
# but will executed if it is run straight from the CLI
# Helps, in testing only this class
if __name__ == '__main__':
    l = Ledger()
    print(l)
