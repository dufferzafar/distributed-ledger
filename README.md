
# distributed-ledger

A dummy bitcoin simulation.

## todo / notes

* kademlia
    - Change model to node per process

    - Use json instead of pickle
        + Or try using pickle.dump proto=2

    - Identifiers:
        + HASH160 for Node ID
        + SHA1 for Key
        + Randbits for Msg ID

<!-- 

* simulation.py
    - Need to use a queue to store port, keys etc. 

* A ledger should be append-only
    - So there should be a way to enforce that no insert/delete/extend calls will work.
    - The rest of the list interface should stay intact

 -->
