from collections import OrderedDict

from itertools import zip_longest


class RoutingTable(object):

    def __init__(self, node_identifier, k=20):

        self.node_identifier = node_identifier
        self.k = k
        self.buckets = [OrderedDict() for _ in range(160)]
        self.replacement_caches = [OrderedDict() for _ in range(160)]

        super(RoutingTable, self).__init__()

    def distance(self, peer_identifier):

        return self.node_identifier ^ peer_identifier

    def bucket_index(self, peer_identifier):

        if not (0 <= peer_identifier < 2**160):
            raise ValueError('peer_identifier should be a number between 0 and 2*160-1.')

        return 160 - self.distance(peer_identifier).bit_length()

    def update_peer(self, peer_identifier, peer):

        if peer_identifier == self.node_identifier:
            return

        bucket_index = self.bucket_index(peer_identifier)
        bucket = self.buckets[bucket_index]

        if peer_identifier in bucket:
            del bucket[peer_identifier]
            bucket[peer_identifier] = peer

        elif len(bucket) < self.k:
            bucket[peer_identifier] = peer

        else:
            replacement_cache = self.replacement_caches[bucket_index]

            if peer_identifier in replacement_cache:
                del replacement_cache[peer_identifier]

            replacement_cache[peer_identifier] = peer

    def forget_peer(self, peer_identifier):

        if peer_identifier == self.node_identifier:
            return

        bucket_index = self.bucket_index(peer_identifier)
        bucket = self.buckets[bucket_index]
        replacement_cache = self.replacement_caches[bucket_index]

        if peer_identifier in bucket:
            del bucket[peer_identifier]

            if len(replacement_cache):
                replacement_identifier, replacement_peer = replacement_cache.popitem()
                bucket[replacement_identifier] = replacement_peer

    def find_closest_peers(self, key, excluding=None, k=None):
        peers = []
        k = k or self.k

        farther = range(self.bucket_index(key), -1, -1)
        closer = range(self.bucket_index(key) + 1, 160, 1)

        for f, c in zip_longest(farther, closer):

            for i in (f, c):

                if i is None:
                    continue

                bucket = self.buckets[i]

                for peer_identifier in reversed(bucket):

                    if peer_identifier == excluding:
                        continue

                    peers.append((peer_identifier, bucket[peer_identifier]))

                    if len(peers) == k:
                        return peers
        return peers
