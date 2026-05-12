"""Traffic generator — six patterns from Module 4."""

import threading
import time
import random
from simulation.packet import Packet


def _send_packet(node, dst_id: str, flow_id: str, size: int, priority: int = 0) -> Packet:
    pkt = Packet(
        src=node.node_id,
        dst=dst_id,
        size_bytes=size,
        sent_time=time.time(),
        flow_id=flow_id,
        priority=priority,
    )
    node.send(pkt)
    return pkt


def cbr(node, dst_id: str, rate_pps: float, duration: float,
         flow_id: str = "cbr", size: int = 1000, priority: int = 0) -> list:
    """Constant Bit Rate: `rate_pps` packets/sec for `duration` seconds."""
    packets = []
    interval = 1.0 / rate_pps
    clock = time.perf_counter
    end = clock() + duration
    deadline = clock() + interval
    while clock() < end:
        pkt = _send_packet(node, dst_id, flow_id, size, priority)
        packets.append(pkt)
        remaining = deadline - clock()
        if remaining > 0:
            time.sleep(remaining)
        deadline += interval
    return packets


def bursty(node, dst_id: str, burst_size: int, idle_s: float, burst_s: float,
           duration: float, flow_id: str = "bursty", size: int = 1000) -> list:
    """Long idle periods then rapid burst of `burst_size` packets."""
    packets = []
    end = time.time() + duration
    while time.time() < end:
        time.sleep(idle_s)
        if time.time() >= end:
            break
        interval = burst_s / burst_size
        for _ in range(burst_size):
            if time.time() >= end:
                break
            pkt = _send_packet(node, dst_id, flow_id, size)
            packets.append(pkt)
            time.sleep(interval)
    return packets


def many_to_one(sources: list, dst_node, duration: float,
                rate_pps: float = 10, flow_id: str = "m2o", size: int = 1000) -> list:
    """All sources send to a single destination concurrently."""
    all_packets = []
    lock = threading.Lock()

    def worker(src):
        pkts = cbr(src, dst_node.node_id, rate_pps, duration,
                   flow_id=f"{flow_id}_{src.node_id}", size=size)
        with lock:
            all_packets.extend(pkts)

    threads = [threading.Thread(target=worker, args=(s,), daemon=True) for s in sources]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return all_packets


def many_to_many(nodes: list, duration: float,
                 rate_pps: float = 5, flow_id: str = "m2m", size: int = 1000) -> list:
    """Random source-destination pairs send concurrently."""
    all_packets = []
    lock = threading.Lock()
    pairs = [(nodes[i], nodes[j]) for i in range(len(nodes))
             for j in range(len(nodes)) if i != j]
                                                               
    sample = random.sample(pairs, min(len(pairs), max(1, len(nodes) // 2)))

    def worker(src, dst):
        pkts = cbr(src, dst.node_id, rate_pps, duration,
                   flow_id=f"{flow_id}_{src.node_id}_{dst.node_id}", size=size)
        with lock:
            all_packets.extend(pkts)

    threads = [threading.Thread(target=worker, args=(s, d), daemon=True) for s, d in sample]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return all_packets


def elephant_flow(node, dst_id: str, duration: float,
                  flow_id: str = "elephant", size: int = 65000) -> list:
    """One huge file transfer: max-size packets as fast as possible."""
    packets = []
    end = time.time() + duration
    while time.time() < end:
        pkt = _send_packet(node, dst_id, flow_id, size)
        packets.append(pkt)
    return packets


def mice_flows(nodes: list, duration: float, n_flows: int = 500,
               flow_id_prefix: str = "mice") -> list:
    """Many tiny short-lived flows (HTTP-like)."""
    all_packets = []
    lock = threading.Lock()

    def one_flow(i):
        src, dst = random.sample(nodes, 2)
        pkts = cbr(src, dst.node_id, rate_pps=20, duration=random.uniform(0.05, 0.3),
                   flow_id=f"{flow_id_prefix}_{i}", size=random.randint(64, 1500))
        with lock:
            all_packets.extend(pkts)

    threads = []
    end = time.time() + duration
    i = 0
    while time.time() < end and i < n_flows:
        t = threading.Thread(target=one_flow, args=(i,), daemon=True)
        t.start()
        threads.append(t)
        time.sleep(duration / n_flows)
        i += 1
    for t in threads:
        t.join(timeout=2)
    return all_packets


def run_in_thread(fn, *args, **kwargs) -> threading.Thread:
    """Helper: run any generator function in a background thread."""
    t = threading.Thread(target=fn, args=args, kwargs=kwargs, daemon=True)
    t.start()
    return t
