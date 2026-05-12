"""Experiment 5: Failover time.

Uses a dedicated topology (topo_failover.json):
  Primary path:  R0 -> A -> R9  (2 hops, 5ms each) -- traditional prefers this
  Backup path:   R0 -> C -> D -> R9  (3 hops, 10ms each)

At t=FAILURE_AT, the A-R9 link is cut.
- SDN: controller removes the edge, recomputes via C-D, pushes rules -> recovery in ms
- Traditional: A waits DEAD_INTERVAL (30s) to declare R9 dead, then
  re-propagates via backup -> recovery in 30+ seconds
"""

import sys, os, time, csv, threading
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from traditional.network import TraditionalNetwork
from sdn.network import SDNNetwork
from experiments.traffic_gen import cbr
from experiments.metrics import compute_recovery_time

TOPO = os.path.join(os.path.dirname(__file__), "..", "topologies", "topo_failover.json")
RESULTS_DIR = os.path.join(os.path.dirname(__file__), "..", "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

DURATION = 55.0
FAILURE_AT = 5.0
RATE_PPS = 30
SRC_ID = "R0"
DST_ID = "R9"
FAIL_LINK = ("A", "R9")


# send traffic, cut the primary link mid-flow, and measure how long until packets get through again
def run_experiment(label: str, network, get_node_fn) -> dict:
    src = get_node_fn(SRC_ID)
    all_sent = []

    traffic_thread = threading.Thread(
        target=lambda: all_sent.extend(
            cbr(src, DST_ID, RATE_PPS, DURATION, flow_id="exp5_main", size=512)
        ),
        daemon=True,
    )
    traffic_thread.start()

    time.sleep(FAILURE_AT)
    failure_wall = time.time()
    print(f"  [{label}] Killing link {FAIL_LINK[0]}<->{FAIL_LINK[1]} at t={FAILURE_AT}s")
    network.fail_link(FAIL_LINK[0], FAIL_LINK[1])

    traffic_thread.join()
    time.sleep(0.1)  # let in-transit packets finish delivering

    recovery = compute_recovery_time(all_sent, failure_wall)
    total_sent_approx = len(all_sent)
    total_received = len([p for p in all_sent if p.received_time is not None])

    result = {
        "label": label,
        "failure_at_s": FAILURE_AT,
        "recovery_time_s": round(recovery, 4) if recovery != float("inf") else -1,
        "total_sent_approx": total_sent_approx,
        "total_received": total_received,
        "packet_loss_pct": round(
            100.0 * (total_sent_approx - total_received) / max(1, total_sent_approx), 2
        ),
    }
    rt = result["recovery_time_s"]
    print(f"  [{label}] Recovery time: {'NEVER' if rt == -1 else f'{rt:.4f}s'}")
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

    print("\n[Traditional] Starting (this takes ~40s for convergence + recovery)...")
    trad = TraditionalNetwork(TOPO, update_interval=2.0)
    trad.start()
    trad.wait_for_convergence(timeout=30)
    r_trad = run_experiment("traditional", trad, lambda nid: trad.routers[nid])
    trad.stop()
    results.append(r_trad)

    print("\n[SDN] Starting...")
    sdn = SDNNetwork(TOPO)
    r_sdn = run_experiment("sdn", sdn, lambda nid: sdn.switches[nid])
    results.append(r_sdn)

    save_csv(results)


if __name__ == "__main__":
    main()
