from utils import random_id


class Transaction:

    def __init__(self, sender, receiver, witness, input_tx=None):

        self.id = random_id()
        self.input_tx = input_tx
        self.sender = sender
        self.receiver = receiver
        self.witness = witness

    def __repr__(self):
        return repr(self.id)
