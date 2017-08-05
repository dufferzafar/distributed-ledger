
import binascii
import hashlib
import random
import threading
import time

import ecdsa


class Node(threading.Thread):

    def __init__(self, _all_nodes):
        threading.Thread.__init__(self)

        # Connection information of a node
        self.ip = "127.0.0.1"
        self.port = random.randint(8000, 9000)

        # Generate key-pair
        sk = ecdsa.SigningKey.generate(curve=ecdsa.SECP256k1)
        vk = sk.get_verifying_key()

        self.pvt_key = binascii.hexlify(sk.to_string())
        self.pub_key = binascii.hexlify(vk.to_string())

        # Generate a 160 bit node id
        # (same as bitcoin wallet id)
        ripemd = hashlib.new('ripemd160')
        ripemd.update(hashlib.sha256(self.pub_key).digest())
        self.id = binascii.hexlify(ripemd.digest())

        _all_nodes.append((
            self.id,
            self.ip,
            self.port,
            self.pub_key,
            self.pvt_key
        ))

    def run(self):

        # Keep this thread running
        while True:
            time.sleep(1)


if __name__ == '__main__':

    # This is used to store node related information
    # that can be used by the simulation controller.
    all_nodes = []

    for _ in range(100):

        Node(all_nodes).start()

    print(len(all_nodes))
