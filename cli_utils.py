import re

import config


# NOTE: This only works because we know this is a simulation running
# on mininet and are aware of each hosts' socket.

# BUG: This has no idea of how many nodes are actually running
def get_sock_from_name(name):
    num = re.findall(r'\d+', name)
    num = int(num[0])

    # TODO: Use some python ip module to get ip based on config.IP
    return (("10.0.0.%d" % (num + 1)), config.PORT)
