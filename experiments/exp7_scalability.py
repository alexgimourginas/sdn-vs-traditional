"""Experiment 7: Scalability — does it still work with 100 nodes?

Repeats Experiments 1 (throughput), 5 (failover), and convergence time
on topologies of 5, 10, 20, 50, 100 nodes.
"""

import sys, os, time, csv, threading
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from traditional.network import TraditionalNetwork
from sdn.network import SDNNetwork
from experiments.traffic_gen import cbr
from experiments.metrics import (
    compute_metrics, compute_recovery_time, compute_convergence_time
)

TOPO_DIR = os.path.join(os.path.dirname(__file__), "..", "topologies")
RESULTS_DIR = os.path.join(os.path.dirname(__file__), "..", "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

SIZES = [5, 10, 20, 50, 100]
DURATION = 3.0
RATE_PPS = 50
FAILURE_AT = 1.5


def topo_path(n):
    return os.path.join(TOPO_DIR, f"topo_{n}.json")


def measure_traditional(n: int) -> dict:
    topo = topo_path(n)
    trad = TraditionalNetwork(topo, update_interval=2.0)
    trad.start()

    conv_time = compute_convergence_time(trad, timeout=120)

    node_ids = trad.node_ids()
    src_id, dst_id = node_ids[0], node_ids[-1]
    src = trad.routers[src_id]

                
    pkts = []
    trad.routers[dst_id].on_packet_received = lambda p: pkts.append(p)
    t0 = time.time()
    cbr(src, dst_id, rate_pps=RATE_PPS, duration=DURATION,
        flow_id="scale_tp", size=1000)
    elapsed = time.time() - t0
    m_tp = compute_metrics(pkts, elapsed)

              
    pkts2 = []
    trad.routers[dst_id].on_packet_received = lambda p: pkts2.append(p)
    traffic_thread = threading.Thread(
        target=cbr,
        args=(src, dst_id, RATE_PPS, DURATION * 4),
        kwargs={"flow_id": "scale_fo", "size": 512},
        daemon=True,
    )
    traffic_thread.start()
    time.sleep(FAILURE_AT)
    failure_wall = time.time()

                                     
    first_neighbor = list(trad.routers[src_id].neighbors.keys())[0]
    trad.fail_link(src_id, first_neighbor)
    traffic_thread.join()
    recovery = compute_recovery_time(pkts2, failure_wall)

    trad.stop()

    return {
        "n_nodes": n,
        "convergence_s": round(conv_time, 3),
        "throughput_mbps": round(m_tp["throughput_mbps"], 4),
        "packet_loss_pct": round(m_tp["packet_loss_pct"], 2),
        "recovery_time_s": round(recovery, 3) if recovery != float("inf") else -1,
    }


def measure_sdn(n: int) -> dict:
    topo = topo_path(n)

    t0 = time.perf_counter()
    sdn = SDNNetwork(topo)
    setup_time = time.perf_counter() - t0                                             

    node_ids = sdn.node_ids()
    src_id, dst_id = node_ids[0], node_ids[-1]
    src = sdn.switches[src_id]

                
    pkts = []
    sdn.switches[dst_id].on_packet_received = lambda p: pkts.append(p)
    t0 = time.time()
    cbr(src, dst_id, rate_pps=RATE_PPS, duration=DURATION,
        flow_id="scale_tp", size=1000)
    elapsed = time.time() - t0
    m_tp = compute_metrics(pkts, elapsed)

              
    pkts2 = []
    sdn.switches[dst_id].on_packet_received = lambda p: pkts2.append(p)
    traffic_thread = threading.Thread(
        target=cbr,
        args=(src, dst_id, RATE_PPS, DURATION * 4),
        kwargs={"flow_id": "scale_fo", "size": 512},
        daemon=True,
    )
    traffic_thread.start()
    time.sleep(FAILURE_AT)
    failure_wall = time.time()

    first_neighbor = list(sdn.switches[src_id].neighbors.keys())[0]
    recompute_t0 = time.perf_counter()
    sdn.fail_link(src_id, first_neighbor)
    recompute_time = time.perf_counter() - recompute_t0

    traffic_thread.join()
    recovery = compute_recovery_time(pkts2, failure_wall)

    return {
        "n_nodes": n,
        "convergence_s": round(setup_time, 6),                 
        "throughput_mbps": round(m_tp["throughput_mbps"], 4),
        "packet_loss_pct": round(m_tp["packet_loss_pct"], 2),
        "recovery_time_s": round(recovery, 6) if recovery != float("inf") else -1,
        "controller_recompute_s": round(recompute_time, 6),
    }


def save_csv(label: str, rows: list):
    if not rows:
        return
    path = os.path.join(RESULTS_DIR, f"exp7_scalability_{label}.csv")
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(f"  Saved {path}")


def main():
    print("\n=== Experiment 7: Scalability ===")

    trad_rows = []
    sdn_rows = []

    for n in SIZES:
        print(f"\n--- n={n} nodes ---")

        print(f"  [Traditional n={n}]")
        try:
            r = measure_traditional(n)
            trad_rows.append(r)
            print(f"    conv={r['convergence_s']}s  tp={r['throughput_mbps']}Mbps  "
                  f"recovery={r['recovery_time_s']}s")
        except Exception as e:
            print(f"    ERROR: {e}")

        print(f"  [SDN n={n}]")
        try:
            r = measure_sdn(n)
            sdn_rows.append(r)
            print(f"    setup={r['convergence_s']}s  tp={r['throughput_mbps']}Mbps  "
                  f"recovery={r['recovery_time_s']}s  "
                  f"recompute={r.get('controller_recompute_s', '?')}s")
        except Exception as e:
            print(f"    ERROR: {e}")

    save_csv("traditional", trad_rows)
    save_csv("sdn", sdn_rows)


if __name__ == "__main__":
    main()
