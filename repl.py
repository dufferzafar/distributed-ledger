from cli_utils import get_sock_from_name


class REPL():
    intro = " Type help or ? to list commands.\n"
    prompt = ">>> "

    def __init__(self, node):
        self.node = node

    def exec_cmd(self, cmd, args):
        try:
            func = getattr(self, 'do_' + cmd)
        except AttributeError:
            print("No command named '%s'" % cmd)
            print("Type 'help' to list commands")

        func(args)

    def do_id(self, args):
        if len(args) == 2:
            peer_socket = (args[0], int(args[1]))
            peer_id = yield from self.node.request(peer_socket, "ping", self.node.identifier)
            print(peer_id)
        else:
            print(self.node.identifier)

    def do_dht(self, args):
        print(self.node.storage_str())

    def do_routing_table(self, args):
        print(self.node.routing_table)

    def do_put(self, args):
        if (len(args) != 2):
            print("Expected 2 arguments, %d given" % len(args))
        else:
            yield from self.node.put(args[0], args[1], hashed=False)

    def do_get(self, args):
        if (len(args) != 1):
            print("Expected 1 argument, %d given" % len(args))
        else:
            try:
                value = yield from self.node.get(args[0], hashed=False)
                print(value)
            except KeyError:
                print("Key not found")

    def do_send_bitcoins(self, args):
        if (len(args) != 4):
            print("Expected 4 arguments, %d given" % len(args))
        else:
            try:
                sender_sock = get_sock_from_name(args[0])
                receiver_sock = get_sock_from_name(args[1])
                witness_sock = get_sock_from_name(args[2])

                receiver_id = yield from self.node.request(receiver_sock, 'ping', self.node.identifier)
                witness_id = yield from self.node.request(witness_sock, 'ping', self.node.identifier)
                amount = int(args[3])

                reply = yield from self.node.request(sender_sock, "send_bitcoins", self.node.identifier, int(receiver_id), int(witness_id), amount)
                print(reply)

            except Exception as e:
                print("Exception Caught : ", e)

    def do_help(self, args):
        print("Haven't implemented yet.")

    # @staticmethod
    # def do_(args):
