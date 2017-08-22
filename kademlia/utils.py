import hashlib
import random


def sha1_int(key):

    if hasattr(key, 'encode'):
        key = key.encode()
    digest = hashlib.sha1(key).digest()
    return int.from_bytes(digest, byteorder='big', signed=False)


def random_id():

    identifier = random.getrandbits(160)
    return sha1_int(identifier.to_bytes(20, byteorder='big', signed=False))
