import binascii
import hashlib
import random

import ecdsa

# This elliptic curve is used by bitcoin too
CURVE = ecdsa.SECP256k1


def sha1_int(key):
    if hasattr(key, 'encode'):
        key = key.encode()

    digest = hashlib.sha1(key).digest()

    return int.from_bytes(digest, byteorder='big', signed=False)


def random_id():
    identifier = random.getrandbits(160)

    return sha1_int(identifier.to_bytes(20, byteorder='big', signed=False))


def gen_pub_pvt():
    """
    Generate key-pair.
    """

    sk = ecdsa.SigningKey.generate(curve=CURVE)
    vk = sk.get_verifying_key()

    pvt_key = binascii.hexlify(sk.to_string()).decode()
    pub_key = binascii.hexlify(vk.to_string()).decode()

    return pub_key, pvt_key


# msg must be a bytes object - NOT str/unicode
def sign_msg(pvt_key, msg):
    pvt_key = binascii.unhexlify(pvt_key.encode())
    sk = ecdsa.SigningKey.from_string(pvt_key, curve=CURVE)

    return sk.sign(msg)


def verify_msg(pub_key, msg, sign):
    pub_key = binascii.unhexlify(pub_key.encode())
    vk = ecdsa.VerifyingKey.from_string(pub_key, curve=CURVE)

    return vk.verify(sign, msg)

if __name__ == '__main__':

    # Test out signing & verification
    msg = b"Shadab Zafar"

    pub, pvt = gen_pub_pvt()

    sign = sign_msg(pvt, msg)

    assert verify_msg(pub, msg, sign)
