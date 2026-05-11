"""Experiment 2: Latency, especially tail latency.

Sends 500 packets between two endpoints while background traffic congests
the network. Measures avg / p50 / p95 / p99 latency.
"""

import sys, os, time, csv, threading
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from traditional.network import TraditionalNetwork
from sdn.network import SDNNetwork
from experiments.traffic_gen import cbr, run_in_thread
from experiments.metrics import compute_metrics

TOPO = os.path.join(os.path.dirname(__file__), "..", "topologies", "topo_10.json")
RESULTS_DIR = os.path.join(os.path.dirname(__file__), "..", "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

N_PACKETS = 500
RATE_PPS = 50
BG_RATE_PPS = 300
DURATION = N_PACKETS / RATE_PPS


def run_experiment(label: str, network, get_node_fn, node_ids: list) -> dict:
    src_id, dst_id = node_ids[0], node_ids[-1]
    mid_id = node_ids[len(node_ids) // 2]
    src = get_node_fn(src_id)
    bg_src = get_node_fn(mid_id)

    packets = []
    get_node_fn(dst_id).on_packet_received = lambda p: packets.append(p)

                                   
    bg_thread = run_in_thread(cbr, bg_src, dst_id,
                              BG_RATE_PPS, DURATION,
                              "bg_congestion", 1500)

    t0 = time.time()
    cbr(src, dst_id, rate_pps=RATE_PPS, duration=DURATION,
        flow_id="exp2_main", size=1000)
    elapsed = time.time() - t0
    bg_thread.join(timeout=1)

    main_packets = [p for p in packets if p.flow_id == "exp2_main"]
    m = compute_metrics(main_packets, elapsed)
    print(f"  [{label}] avg={m['latency_avg_ms']:.2f}ms  "
          f"p95={m['latency_p95_ms']:.2f}ms  "
          f"p99={m['latency_p99_ms']:.2f}ms  "
          f"loss={m['packet_loss_pct']:.1f}%")
    return m


def save_csv(label: str, m: dict):
    path = os.path.join(RESULTS_DIR, f"exp2_latency_{label}.csv")
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=m.keys())
        writer.writeheader()
        writer.writerow(m)
    print(f"  Saved {path}")


def main():
    print("\n=== Experiment 2: Latency (especially tail latency) ===")

    print("\n[Traditional] Starting...")
    trad = TraditionalNetwork(TOPO, update_interval=2.0)
    trad.start()
    trad.wait_for_convergence(timeout=30)
    m_trad = run_experiment("traditional", trad,
                            lambda nid: trad.routers[nid], trad.node_ids())
    trad.stop()
    save_csv("traditional", m_trad)

    print("\n[SDN] Starting...")
    sdn = SDNNetwork(TOPO)
    m_sdn = run_experiment("sdn", sdn,
                           lambda nid: sdn.switches[nid], sdn.node_ids())
    save_csv("sdn", m_sdn)


if __name__ == "__main__":
    main()
