import re


def get_sock_from_name(name):
    num = re.findall(r'\d+', name)
    num = int(num[0])

    return (("10.0.0.%d" % (num + 1)), (9000 + num))
