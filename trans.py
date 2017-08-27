from utils import random_id


class Transaction:

    def __init__(self, sender, receiver, witness, input_tx=None):

        self.id = random_id()
        self.input_tx = input_tx
        self.sender = sender
        self.receiver = receiver
        self.witness = witness

    def __eq__(self, other):
        return self.id == other.id  # no need to compare other attributes id must be unique

    def __repr__(self):
        return repr(self.id)
