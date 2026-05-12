"""Experiment 4: Packet loss under stress / DDoS-like attack.

Both attack and legitimate traffic originate from the same node so they
share the exact same path. All links are given a small queue (max_queue=3).
At 1000 pps attack traffic the queue fills up and legitimate packets get
dropped in traditional (no QoS). In SDN, legitimate packets carry priority=1
which bypasses the queue limit, so they always get through.
"""

import sys, os, time, csv
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from traditional.network import TraditionalNetwork
from sdn.network import SDNNetwork
from experiments.traffic_gen import cbr, run_in_thread
from experiments.metrics import compute_metrics

TOPO = os.path.join(os.path.dirname(__file__), "..", "topologies", "topo_10.json")
RESULTS_DIR = os.path.join(os.path.dirname(__file__), "..", "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

DURATION = 5.0
LEGIT_RATE = 20
ATTACK_RATE = 1000
BOTTLENECK_QUEUE = 3


# set a small queue on every link to simulate a congested bottleneck
def _apply_queue_limits(network):
    for link in network.links:
        link.max_queue = BOTTLENECK_QUEUE


# flood attack traffic while sending legitimate priority=1 traffic and measure how much survives
def run_experiment(label: str, network, get_node_fn, node_ids: list) -> dict:
    _apply_queue_limits(network)

    src_id = node_ids[0]
    dst_id = node_ids[-1]
    src = get_node_fn(src_id)

    atk_thread = run_in_thread(cbr, src, dst_id,
                               ATTACK_RATE, DURATION, "attack", 1500, 0)

    t0 = time.time()
    legit_sent = cbr(src, dst_id, rate_pps=LEGIT_RATE, duration=DURATION,
                     flow_id="legit", size=512, priority=1)
    elapsed = time.time() - t0
    atk_thread.join(timeout=1)
    time.sleep(0.1)  # let in-transit packets finish

    m = compute_metrics(legit_sent, elapsed)
    m["legit_rate_pps"] = LEGIT_RATE
    m["attack_rate_pps"] = ATTACK_RATE
    print(f"  [{label}] legit received={m['total_received']}/{m['total_sent']}  "
          f"loss={m['packet_loss_pct']:.1f}%")
    return m


def save_csv(label: str, m: dict):
    path = os.path.join(RESULTS_DIR, f"exp4_packet_loss_{label}.csv")
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=m.keys())
        writer.writeheader()
        writer.writerow(m)
    print(f"  Saved {path}")


def main():
    print("\n=== Experiment 4: Packet loss under stress/attack ===")

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
