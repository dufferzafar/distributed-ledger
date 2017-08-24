
# distributed-ledger

A dummy bitcoin simulation.

## todo / notes

* kademlia
    - Identifiers:
        + HASH160 for Node ID
        + SHA1 for Key
        + Randbits for Msg ID

* Use hexadecimal/base64 node ids
    - Separate message identifier class that is an int
    - But gets printed as base 64?

* Break datagramrpc into a separate file and implement non-kademlia functions there?

* On stopping the mininet-network kill all xterms

<!-- 

* simulation.py
    - Need to use a queue to store port, keys etc. 

* A ledger should be append-only
    - So there should be a way to enforce that no insert/delete/extend calls will work.
    - The rest of the list interface should stay intact

-->
