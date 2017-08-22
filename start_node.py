import sys
import asyncio

from kademlia import KademliaNode


def start_a_node(sock_addr, bootstrap_addr=None):

    print (sock_addr[0],sock_addr[1])# just to check running or not
    loop = asyncio.get_event_loop()

    f = loop.create_datagram_endpoint(KademliaNode, local_addr=sock_addr)
    _, node = loop.run_until_complete(f)

    # TODO: Will this work? Test!
    if bootstrap_addr:
        loop.run_until_complete(node.ping(bootstrap_addr, node.identifier))

    loop.run_forever()


if __name__ == '__main__':

    # TODO: Improved argument parsing via docopt or click
    
    if len(sys.argv)==5:
        start_a_node(   
            sock_addr=(sys.argv[1], int(sys.argv[2])),bootstrap_addr=(sys.argv[3], int(sys.argv[4]))
        )
    else:
        start_a_node(
                  sock_addr=(sys.argv[1], int(sys.argv[2]))
        )

