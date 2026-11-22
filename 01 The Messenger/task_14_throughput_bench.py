#!/usr/bin/env python3
import sys
import json
import time

class Node:
    def __init__(self):
        self.node_id = None
        self.node_ids = []
        self.next_msg_id = 0
        self.start_time = None
        self.message_count = 0
        self.latencies = []  # microseconds

    def send(self, dest, body):
        body["msg_id"] = self.next_msg_id
        self.next_msg_id += 1
        message = {"src": self.node_id, "dest": dest, "body": body}
        print(json.dumps(message), flush=True)

    def reply(self, request, body):
        body["in_reply_to"] = request["body"]["msg_id"]
        self.send(request["src"], body)

    def record_latency(self, start_time):
        latency_us = int((time.monotonic() - start_time) * 1_000_000)
        self.latencies.append(latency_us)
        return latency_us

    def get_average_latency(self):
        if len(self.latencies) == 0:
            return 0
        return int(sum(self.latencies) / len(self.latencies))

    def get_percentile(self, percentile):
        if len(self.latencies) == 0:
            return 0
        self.latencies.sort()
        return self.latencies[int(len(self.latencies) / 100 * percentile) - 1]

    def handle_bench_echo(self, message, recv_time):
        self.message_count += 1
        body = message["body"]
        latency_us = self.record_latency(recv_time)
        self.reply(message, {"type": "bench_echo_ok", "echo": body["echo"], "latency_us": latency_us})

    def handle_bench_stats(self, message, recv_time):
        elapsed_ms = int((recv_time - self.start_time) * 1_000)
        avg_latency = self.get_average_latency()
        throughput_per_sec = 0

        if elapsed_ms != 0:
            throughput_per_sec = self.message_count / elapsed_ms * 1_000
        
        self.reply(message, {
            "type": "bench_stats_ok", 
            "total_messages": self.message_count, 
            "elapsed_ms": elapsed_ms,
            "throughput_per_sec": throughput_per_sec,
            "avg_latency_us": avg_latency,
            "p99_latency_us": self.get_percentile(99)})

def main():
    node = Node()

    for line in sys.stdin:
        recv_time = time.monotonic()
        line = line.strip()
        if not line:
            continue
        message = json.loads(line)
        body = message["body"]
        msg_type = body["type"]

        if node.start_time is None:
            node.start_time = recv_time

        if msg_type == "init":
            node.node_id = body["node_id"]
            node.node_ids = body["node_ids"]
            node.reply(message, {"type": "init_ok"})
        elif msg_type == "echo":
            node.reply(message, {"type": "echo_ok", "echo": body["echo"]})
        elif msg_type == "bench_echo":
            node.handle_bench_echo(message, recv_time)
        elif msg_type == "bench_stats":
            node.handle_bench_stats(message, recv_time)
            pass

if __name__ == "__main__":
    main()
