"""Experiment 3: Jitter (for VoIP / video calls).

Sends CBR at 50 packets/sec for 10 seconds and measures inter-arrival
time standard deviation. Lower is better for real-time traffic.
"""

import sys, os, time, csv, ctypes
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from traditional.network import TraditionalNetwork
from sdn.network import SDNNetwork
from experiments.traffic_gen import cbr
from experiments.metrics import compute_metrics

TOPO = os.path.join(os.path.dirname(__file__), "..", "topologies", "topo_10.json")
RESULTS_DIR = os.path.join(os.path.dirname(__file__), "..", "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

RATE_PPS = 50
DURATION = 10.0


# send a steady CBR stream and measure how consistent the inter-arrival times are
def run_experiment(label: str, network, get_node_fn, node_ids: list) -> dict:
    src_id, dst_id = node_ids[0], node_ids[-1]
    src = get_node_fn(src_id)
    packets = []
    get_node_fn(dst_id).on_packet_received = lambda p: packets.append(p)

    t0 = time.time()
    cbr(src, dst_id, rate_pps=RATE_PPS, duration=DURATION,
        flow_id="exp3_voip", size=200)
    elapsed = time.time() - t0

    # jitter_ms is the standard deviation of inter-arrival times -- lower means smoother
    m = compute_metrics(packets, elapsed)
    print(f"  [{label}] jitter={m['jitter_ms']:.3f}ms  "
          f"avg_latency={m['latency_avg_ms']:.2f}ms  "
          f"loss={m['packet_loss_pct']:.1f}%")
    return m


def save_csv(label: str, m: dict):
    path = os.path.join(RESULTS_DIR, f"exp3_jitter_{label}.csv")
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=m.keys())
        writer.writeheader()
        writer.writerow(m)
    print(f"  Saved {path}")


def main():
    print("\n=== Experiment 3: Jitter (VoIP / video) ===")
    if sys.platform == "win32":
        ctypes.windll.winmm.timeBeginPeriod(1)

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

    if sys.platform == "win32":
        ctypes.windll.winmm.timeEndPeriod(1)


if __name__ == "__main__":
    main()
