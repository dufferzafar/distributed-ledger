
# distributed-ledger

A dummy bitcoin simulation.

## todo

* Sign & Verify transactions

* Print ledger - group'ed by node id - display sum

* Set log level from cli.py

* Discuss exactly how we'll demo each task

---

From the [Assignment PDF](http://www.cse.iitd.ernet.in/~mcs162658/cop701/A1.pdf)

* Node suddenly chooses to become offline

* For 2PC 
    * With some random probability, a node decides to say "abort"
    * Each transaction is uniquely identified by its scalar Lamport clock:  node id, local transaction number (monotonically increasing sequence)
