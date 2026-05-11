"""Metrics collector — Module 6.

All functions take a list of Packet objects and return a dict of computed metrics.
"""

import statistics
import time
from simulation.packet import Packet


def compute_metrics(packets: list, elapsed_s: float) -> dict:
    """Compute all Module 6 metrics from a packet list."""
    received = [p for p in packets if p.received_time is not None and not p.dropped]
    dropped = [p for p in packets if p.dropped or p.received_time is None]

    total_sent = len(packets)
    total_received = len(received)
    total_bytes = sum(p.size_bytes for p in received)

    latencies = [p.latency() for p in received if p.latency() is not None]
    latencies.sort()

    inter_arrivals = _inter_arrivals(received)

    return {
        "total_sent": total_sent,
        "total_received": total_received,
        "packet_loss_pct": _loss_pct(total_sent, total_received),
        "throughput_mbps": _throughput(total_bytes, elapsed_s),
        "latency_avg_ms": _ms(statistics.mean(latencies)) if latencies else None,
        "latency_median_ms": _ms(statistics.median(latencies)) if latencies else None,
        "latency_p95_ms": _ms(_percentile(latencies, 95)) if latencies else None,
        "latency_p99_ms": _ms(_percentile(latencies, 99)) if latencies else None,
        "latency_max_ms": _ms(max(latencies)) if latencies else None,
        "jitter_ms": _ms(statistics.stdev(inter_arrivals)) if len(inter_arrivals) > 1 else 0.0,
    }


def compute_recovery_time(packets: list, failure_time: float) -> float:
    """Return seconds from failure_time until the first packet arrived after it.

    Returns float('inf') if no packet ever arrived after the failure.
    """
    post_failure = [
        p for p in packets
        if p.received_time is not None and p.received_time > failure_time
    ]
    if not post_failure:
        return float("inf")
    first_after = min(post_failure, key=lambda p: p.received_time)
    return first_after.received_time - failure_time


def compute_convergence_time(network, timeout: float = 120.0) -> float:
    """Measure how long a traditional network takes to converge.

    Starts the network, polls until all routers have full tables.
    Returns elapsed seconds.
    """
    start = time.time()
    all_ids = network.node_ids()
    while time.time() - start < timeout:
        if all(r.convergence_complete(all_ids) for r in network.routers.values()):
            return time.time() - start
        time.sleep(0.05)
    return timeout                     


def compute_config_time_traditional(n_devices: int,
                                    commands_per_device: int = 8,
                                    seconds_per_command: float = 0.5) -> dict:
    """Simulate per-device CLI configuration time for the traditional network."""
    total_commands = n_devices * commands_per_device
    total_time = total_commands * seconds_per_command
    return {
        "devices_touched": n_devices,
        "total_commands": total_commands,
        "config_time_s": total_time,
    }


def compute_config_time_sdn(n_devices: int, commands_per_policy: int = 1) -> dict:
    """SDN: one command to the controller regardless of network size."""
    import time as _time
    t0 = _time.perf_counter()
                                        
    _time.sleep(0.001 * n_devices)                                  
    elapsed = _time.perf_counter() - t0
    return {
        "devices_touched": n_devices,                                                 
        "total_commands": commands_per_policy,
        "config_time_s": elapsed,
    }


def summary_table(label: str, metrics: dict) -> str:
    """Pretty-print a metrics dict."""
    lines = [f"\n{'='*50}", f"  {label}", f"{'='*50}"]
    for k, v in metrics.items():
        if v is None:
            lines.append(f"  {k:35s}: N/A")
        elif isinstance(v, float):
            lines.append(f"  {k:35s}: {v:.4f}")
        else:
            lines.append(f"  {k:35s}: {v}")
    lines.append("=" * 50)
    return "\n".join(lines)


                                                                    
           
                                                                    

def _loss_pct(sent: int, received: int) -> float:
    if sent == 0:
        return 0.0
    return 100.0 * (sent - received) / sent


def _throughput(total_bytes: int, elapsed_s: float) -> float:
    if elapsed_s <= 0:
        return 0.0
    return (total_bytes * 8) / (elapsed_s * 1_000_000)         


def _percentile(sorted_data: list, p: float) -> float:
    if not sorted_data:
        return 0.0
    k = (len(sorted_data) - 1) * p / 100
    f = int(k)
    c = f + 1
    if c >= len(sorted_data):
        return sorted_data[-1]
    return sorted_data[f] + (k - f) * (sorted_data[c] - sorted_data[f])


def _ms(seconds: float) -> float:
    return seconds * 1000.0


def _inter_arrivals(received: list) -> list:
    if len(received) < 2:
        return []
    times = sorted(p.received_time for p in received)
    return [times[i + 1] - times[i] for i in range(len(times) - 1)]
