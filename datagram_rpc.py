import asyncio
import pickle
import logging
import socket

from utils import sha1_int, random_id
logger = logging.getLogger(__name__)


class DatagramRPCProtocol(asyncio.DatagramProtocol):

    def __init__(self, reply_timeout=5):

        self.outstanding_requests = {}
        self.reply_functions = self.find_reply_functions()
        self.reply_timeout = reply_timeout

        super(DatagramRPCProtocol, self).__init__()

    # TODO: Hardcode the reply_functions dict?
    def find_reply_functions(self):
        return {
            func.remote_name: func.reply_function
            for func in self.__class__.__dict__.values()
            if hasattr(func, 'remote_name')
        }

    def connection_made(self, transport):
        logger.info('connection_made: %r', transport)

        self.transport = transport

    def datagram_received(self, data, peer):
        logger.info('data_received: %r, %r', peer, data)
        msg_type, message_identifier, *details = pickle.loads(data)

        if msg_type == 'request':
            procedure_name, args, kwargs = details
            self.request_received(peer, message_identifier, procedure_name, args, kwargs)

        elif msg_type == 'reply':
            response = details[0]
            self.reply_received(peer, message_identifier, response)

    def request_received(self, peer, message_identifier, procedure_name, args, kwargs):
        logger.info('received request from %r: %r(*%r, **%r) as message %r',
                    peer, procedure_name, args, kwargs, message_identifier)

        reply_function = self.reply_functions[procedure_name]
        response = reply_function(self, peer, *args, **kwargs)
        self.reply(peer, message_identifier, response)

    def reply_received(self, peer, message_identifier, response):
        logger.info('received reply to message %r, response %r', message_identifier, response)

        if message_identifier in self.outstanding_requests:
            reply = self.outstanding_requests.pop(message_identifier)
            reply.set_result(response)

    def reply_timed_out(self, message_identifier):
        if message_identifier in self.outstanding_requests:
            reply = self.outstanding_requests.pop(message_identifier)
            reply.set_exception(socket.timeout)

    def request(self, peer, procedure_name, *args, **kwargs):  # args[0] must always be senders nodeid
        message_identifier = random_id()

        logger.info("sending request to %r: %r(*%r, **%r) as message %r",
                    peer, procedure_name, args, kwargs, message_identifier)

        reply = asyncio.Future()
        self.outstanding_requests[message_identifier] = reply

        loop = asyncio.get_event_loop()
        loop.call_later(self.reply_timeout, self.reply_timed_out, message_identifier)

        obj = ('request', message_identifier, procedure_name, args, kwargs)
        message = pickle.dumps(obj, protocol=0)
        self.transport.sendto(message, peer)

        return reply

    def reply(self, peer, message_identifier, response):
        logger.info("sending reply to %r: (%r, %r)",
                    peer, message_identifier, response)

        obj = ('reply', message_identifier, response)
        message = pickle.dumps(obj, protocol=0)

        self.transport.sendto(message, peer)
