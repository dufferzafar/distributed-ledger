import binascii
import hashlib
import random

import ecdsa


def sha1_int(key):
    if hasattr(key, 'encode'):
        key = key.encode()

    digest = hashlib.sha1(key).digest()

    return int.from_bytes(digest, byteorder='big', signed=False)


def random_id():
    identifier = random.getrandbits(160)

    return sha1_int(identifier.to_bytes(20, byteorder='big', signed=False))


def gen_pub_pvt():
    """ Generate key-pair. """

    sk = ecdsa.SigningKey.generate(curve=ecdsa.SECP256k1)
    vk = sk.get_verifying_key()

    pvt_key = binascii.hexlify(sk.to_string()).decode()
    pub_key = binascii.hexlify(vk.to_string()).decode()

    return pub_key, pvt_key


if __name__ == '__main__':
    print(gen_pub_pvt())
