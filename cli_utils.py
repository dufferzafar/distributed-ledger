import re

import config


def get_sock_from_name(name):
    num = re.findall(r'\d+', name)
    num = int(num[0])

    # TODO: Use some python ip module to get ip based on config.IP
    return (("10.0.0.%d" % (num + 1)), config.PORT)
