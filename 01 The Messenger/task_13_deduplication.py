#!/usr/bin/env python3
import sys
import json
from collections import OrderedDict

class LRUCache:
    def __init__(self, capacity=1000):
        self.capacity = capacity
        self.cache = OrderedDict()

    def contains(self, key):
        result = key in self.cache
        if result:
            self.cache.move_to_end(key)
        return result

    def add(self, key):
        self.cache[key] = 0
        if self.size() > self.capacity:
            self.cache.popitem(last=False)

    def size(self):
        return len(self.cache)

class Node:
    def __init__(self):
        self.node_id = None
        self.node_ids = []
        self.next_msg_id = 0
        self.seen = LRUCache(capacity=1000)
        self.total_messages = 0
        self.duplicate_count = 0

    def send(self, dest, body):
        body["msg_id"] = self.next_msg_id
        self.next_msg_id += 1
        message = {"src": self.node_id, "dest": dest, "body": body}
        print(json.dumps(message), flush=True)

    def reply(self, request, body):
        body["in_reply_to"] = request["body"]["msg_id"]
        self.send(request["src"], body)

    def is_duplicate(self, src, msg_id):
        return self.seen.contains((src, msg_id))

    def handle_dedup_echo(self, message):
        self.total_messages += 1
        is_dup = self.is_duplicate(message["src"], message["body"]["msg_id"])
        if not is_dup:
            self.seen.add((message["src"], message["body"]["msg_id"]))
        else:
            self.duplicate_count += 1
        self.reply(message, {"type": "dedup_echo_ok",  "echo": message["body"]["echo"], "was_duplicate": is_dup})

    def handle_dedup_stats(self, message):
        self.reply(message, {"type": "dedup_stats_ok", "total": self.total_messages, "duplicates": self.duplicate_count, "cache_size": self.seen.size()})

def main():
    node = Node()

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        message = json.loads(line)
        body = message["body"]
        msg_type = body["type"]

        if msg_type == "init":
            node.node_id = body["node_id"]
            node.node_ids = body["node_ids"]
            node.reply(message, {"type": "init_ok"})
        elif msg_type == "echo":
            node.reply(message, {"type": "echo_ok", "echo": body["echo"]})
        elif msg_type == "dedup_echo":
            node.handle_dedup_echo(message)
        elif msg_type == "dedup_stats":
            node.handle_dedup_stats(message)

if __name__ == "__main__":
    main()
