"""Experiment 5: Failover time — the big one.

Establishes a stable flow, kills the primary link at t=FAILURE_AT, and
measures how long until the first packet arrives via the alternate path.

Traditional (distance-vector): typically 15–30 seconds.
SDN: typically <1 second (controller recomputes and pushes rules instantly).
"""

import sys, os, time, csv, threading
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from traditional.network import TraditionalNetwork
from sdn.network import SDNNetwork
from experiments.traffic_gen import cbr
from experiments.metrics import compute_recovery_time

TOPO = os.path.join(os.path.dirname(__file__), "..", "topologies", "topo_10.json")
RESULTS_DIR = os.path.join(os.path.dirname(__file__), "..", "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

DURATION = 20.0                                          
FAILURE_AT = 5.0                                                     
RATE_PPS = 30


def _find_primary_link(network, src_id: str, dst_id: str):
    """Return (a, b) of the first link on the shortest path src->dst."""
    import json
                                                                   
    routers = getattr(network, "routers", None)
    if routers:
        current = src_id
        visited = {current}
        for _ in range(20):
            r = routers[current]
            entry = r.get_routing_table().get(dst_id)
            if entry is None:
                break
            next_hop = entry[0]
            if next_hop == dst_id or next_hop == current:
                return (current, next_hop)
            if next_hop in visited:
                break
            a, b = min(current, next_hop), max(current, next_hop)
            visited.add(next_hop)
            current = next_hop
        return (src_id, list(routers[src_id].neighbors.keys())[0])

                                              
    switches = getattr(network, "switches", None)
    if switches:
        path = network.controller.compute_path(src_id, dst_id)
        if path and len(path) >= 2:
            return (path[0], path[1])
    return None


def run_experiment(label: str, network, get_node_fn, node_ids: list) -> dict:
    src_id, dst_id = node_ids[0], node_ids[-1]
    src = get_node_fn(src_id)

    all_received = []
    lock = threading.Lock()
    get_node_fn(dst_id).on_packet_received = lambda p: (
        lock.acquire() or all_received.append(p) or lock.release()
    )

                                    
    start_wall = time.time()

                                   
    traffic_thread = threading.Thread(
        target=cbr,
        args=(src, dst_id, RATE_PPS, DURATION),
        kwargs={"flow_id": "exp5_main", "size": 512},
        daemon=True,
    )
    traffic_thread.start()

                                     
    time.sleep(FAILURE_AT)
    failure_wall = time.time()
    link_pair = _find_primary_link(network, src_id, dst_id)
    if link_pair:
        a, b = link_pair
        print(f"  [{label}] Killing link {a}<->{b} at t={FAILURE_AT}s")
        network.fail_link(a, b)
    else:
        print(f"  [{label}] Warning: could not identify primary link")

    traffic_thread.join()

    recovery = compute_recovery_time(all_received, failure_wall)
    total_received = len(all_received)
    total_sent_approx = int(RATE_PPS * DURATION)

    result = {
        "label": label,
        "failure_at_s": FAILURE_AT,
        "recovery_time_s": recovery if recovery != float("inf") else -1,
        "total_sent_approx": total_sent_approx,
        "total_received": total_received,
        "packet_loss_pct": 100.0 * (total_sent_approx - total_received) / max(1, total_sent_approx),
    }
    print(f"  [{label}] Recovery time: "
          f"{'NEVER' if recovery == float('inf') else f'{recovery:.3f}s'}")
    return result


def save_csv(results: list):
    path = os.path.join(RESULTS_DIR, "exp5_failover.csv")
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)
    print(f"  Saved {path}")


def main():
    print("\n=== Experiment 5: Failover time ===")
    results = []

    print("\n[Traditional] Starting...")
    trad = TraditionalNetwork(TOPO, update_interval=2.0)
    trad.start()
    trad.wait_for_convergence(timeout=30)
    r_trad = run_experiment("traditional", trad,
                            lambda nid: trad.routers[nid], trad.node_ids())
    trad.stop()
    results.append(r_trad)

    print("\n[SDN] Starting...")
    sdn = SDNNetwork(TOPO)
    r_sdn = run_experiment("sdn", sdn,
                           lambda nid: sdn.switches[nid], sdn.node_ids())
    results.append(r_sdn)

    save_csv(results)


if __name__ == "__main__":
    main()
