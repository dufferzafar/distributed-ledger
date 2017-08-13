import asyncio

from functools import wraps

import pickle
import socket


class DatagramRPCProtocol(asyncio.DatagramProtocol):

    def __init__(self, reply_timeout=5):

        self.outstanding_requests = {}
        self.reply_functions = self.find_reply_functions()
        self.reply_timeout = reply_timeout

        super(DatagramRPCProtocol, self).__init__()

    def find_reply_functions(self):
        return {func.remote_name: func.reply_function
                for func in self.__class__.__dict__.values()
                if hasattr(func, 'remote_name')}

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, peer):
        direction, message_identifier, *details = pickle.loads(data)

        if direction == 'request':
            procedure_name, args, kwargs = details
            self.request_received(peer, message_identifier, procedure_name, args, kwargs)

        elif direction == 'reply':
            answer, _ = details
            self.reply_received(peer, message_identifier, answer)

