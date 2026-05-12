"""Experiment 1: Throughput under increasing load.

Ramps offered load from 1 Mbps to 500 Mbps (via increasing packet rate)
on both networks and records delivered throughput at each step.
"""

import sys, os, time, csv
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from traditional.network import TraditionalNetwork
from sdn.network import SDNNetwork
from experiments.traffic_gen import cbr
from experiments.metrics import compute_metrics

TOPO = os.path.join(os.path.dirname(__file__), "..", "topologies", "topo_10.json")
RESULTS_DIR = os.path.join(os.path.dirname(__file__), "..", "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

                                                             
PACKET_SIZE = 1500
DURATION = 3.0                                  
RATES_PPS = [10, 50, 100, 200, 400, 700, 1000, 2000, 4000]                


def mbps_offered(rate_pps: int) -> float:
    return (rate_pps * PACKET_SIZE * 8) / 1_000_000


def run_one(network, node_ids: list, get_node_fn, rate_pps: int) -> dict:
    src_id, dst_id = node_ids[0], node_ids[-1]
    src = get_node_fn(src_id)

    all_packets = []
    src.on_packet_received = None
    dst = get_node_fn(dst_id)
    dst.on_packet_received = lambda p: all_packets.append(p)

    t0 = time.time()
    cbr(src, dst_id, rate_pps=rate_pps, duration=DURATION,
        flow_id="exp1", size=PACKET_SIZE)
    elapsed = time.time() - t0

    m = compute_metrics(all_packets, elapsed)
    m["offered_mbps"] = mbps_offered(rate_pps)
    m["rate_pps"] = rate_pps
    return m


def run_experiment(label: str, network, get_node_fn, node_ids: list) -> list:
    results = []
    for rate in RATES_PPS:
        m = run_one(network, node_ids, get_node_fn, rate)
        print(f"  [{label}] {m['offered_mbps']:.1f} Mbps offered -> "
              f"{m['throughput_mbps']:.3f} Mbps delivered  "
              f"(loss {m['packet_loss_pct']:.1f}%)")
        results.append(m)
    return results


def save_csv(label: str, results: list):
    path = os.path.join(RESULTS_DIR, f"exp1_throughput_{label}.csv")
    if not results:
        return
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)
    print(f"  Saved {path}")


def main():
    print("\n=== Experiment 1: Throughput under increasing load ===")

                         
    print("\n[Traditional] Starting network and waiting for convergence...")
    trad = TraditionalNetwork(TOPO, update_interval=2.0)
    trad.start()
    conv = trad.wait_for_convergence(timeout=30)
    print(f"[Traditional] Converged in {conv:.1f}s")
    trad_results = run_experiment("traditional", trad,
                                  lambda nid: trad.routers[nid], trad.node_ids())
    trad.stop()
    save_csv("traditional", trad_results)

                 
    print("\n[SDN] Starting network...")
    sdn = SDNNetwork(TOPO)
    sdn_results = run_experiment("sdn", sdn,
                                 lambda nid: sdn.switches[nid], sdn.node_ids())
    save_csv("sdn", sdn_results)

    print("\nDone. Run graphs/report_gen.py to generate charts.")


if __name__ == "__main__":
    main()
