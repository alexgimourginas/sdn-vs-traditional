"""
Live Demo Script
Runs in ~35 seconds. Shows:
  1. Both networks starting up
  2. Link failure -- traditional never recovers, SDN recovers in ms
  3. Policy deployment -- traditional touches every device, SDN does it in one call
"""

import sys, os, time, threading
sys.path.insert(0, os.path.dirname(__file__))

from traditional.network import TraditionalNetwork
from sdn.network import SDNNetwork
from sdn import policies as P
from experiments.traffic_gen import cbr
from experiments.metrics import compute_recovery_time

TOPO_SMALL  = "topologies/topo_failover.json"
TOPO_POLICY = "topologies/topo_20.json"
RATE_PPS    = 20
FAILURE_AT  = 5.0
DURATION    = 30.0

def separator():
    print("\n" + "="*55)

def section(title):
    separator()
    print(f"  {title}")
    separator()


def demo_failover():
    section("PART 1: Link Failure and Recovery")

    print("\nTopology: R0 -> A -> R9  (primary, 2 hops)")
    print("          R0 -> C -> D -> R9  (backup, 3 hops)")
    print(f"\nPlan: send traffic for {FAILURE_AT}s, then cut link A->R9")
    print("      measure how long until each network recovers\n")

    # --- Traditional ---
    print("[Traditional] Starting 10 routers with distance-vector routing...")
    trad = TraditionalNetwork(TOPO_SMALL, update_interval=2.0)
    trad.start()
    trad.wait_for_convergence(timeout=20)
    print("[Traditional] Network converged. Sending packets...")

    trad_sent = []
    trad_thread = threading.Thread(
        target=lambda: trad_sent.extend(
            cbr(trad.routers["R0"], "R9", RATE_PPS, DURATION,
                flow_id="demo", size=512)
        ), daemon=True
    )
    trad_thread.start()
    time.sleep(FAILURE_AT)
    fail_wall_trad = time.time()
    print(f"[Traditional] >>> LINK A<->R9 CUT at t={FAILURE_AT}s <<<")
    trad.fail_link("A", "R9")
    trad_thread.join()
    trad.stop()

    trad_recovery = compute_recovery_time(trad_sent, fail_wall_trad)
    trad_received = len([p for p in trad_sent if p.received_time is not None])
    print(f"[Traditional] Packets sent: {len(trad_sent)}  |  Received: {trad_received}")
    print(f"[Traditional] Recovery time: {'NEVER RECOVERED' if trad_recovery == float('inf') else f'{trad_recovery:.3f}s'}")

    print()

    # --- SDN ---
    print("[SDN] Starting controller + 5 switches...")
    sdn = SDNNetwork(TOPO_SMALL)
    print("[SDN] Controller loaded full topology. Sending packets...")

    sdn_sent = []
    sdn_thread = threading.Thread(
        target=lambda: sdn_sent.extend(
            cbr(sdn.switches["R0"], "R9", RATE_PPS, DURATION,
                flow_id="demo", size=512)
        ), daemon=True
    )
    sdn_thread.start()
    time.sleep(FAILURE_AT)
    fail_wall_sdn = time.time()
    print(f"[SDN] >>> LINK A<->R9 CUT at t={FAILURE_AT}s <<<")
    sdn.fail_link("A", "R9")
    print("[SDN] Controller recomputed paths and pushed rules to all switches.")
    sdn_thread.join()
    time.sleep(0.1)

    sdn_recovery = compute_recovery_time(sdn_sent, fail_wall_sdn)
    sdn_received = len([p for p in sdn_sent if p.received_time is not None])
    print(f"[SDN] Packets sent: {len(sdn_sent)}  |  Received: {sdn_received}")
    print(f"[SDN] Recovery time: {sdn_recovery:.4f}s")

    separator()
    print(f"\n  RESULT:")
    print(f"  Traditional  ->  {'No recovery' if trad_recovery == float('inf') else f'{trad_recovery:.3f}s'}  ({trad_received}/{len(trad_sent)} packets delivered)")
    print(f"  SDN          ->  {sdn_recovery:.4f}s  ({sdn_received}/{len(sdn_sent)} packets delivered)")
    separator()


def demo_policy():
    section("PART 2: Policy Deployment")

    print("\nScenario: security team detects a compromised laptop.")
    print("Need to quarantine it across the entire 20-device network.\n")

    sdn = SDNNetwork(TOPO_POLICY)
    node_ids = sdn.node_ids()
    n = len(node_ids)

    CMDS_PER_DEVICE = 8
    SEC_PER_CMD     = 0.05

    print(f"[Traditional] Logging into {n} devices, typing {CMDS_PER_DEVICE} commands each...")
    t0 = time.time()
    time.sleep(n * CMDS_PER_DEVICE * SEC_PER_CMD)
    trad_time = time.time() - t0
    print(f"[Traditional] Done. Time: {trad_time:.1f}s  |  Commands typed: {n * CMDS_PER_DEVICE}  |  Devices touched: {n}")

    print()
    print("[SDN] Sending one quarantine command to controller...")
    policy, _ = P.quarantine("10.0.0.99", node_ids)
    t0 = time.perf_counter()
    sdn.controller.add_policy(policy)
    sdn_time = time.perf_counter() - t0
    print(f"[SDN] Done. Time: {sdn_time*1000:.2f}ms  |  Commands typed: 1  |  Devices touched: 1 (controller)")

    separator()
    print(f"\n  RESULT:")
    print(f"  Traditional  ->  {trad_time:.1f}s,  {n * CMDS_PER_DEVICE} CLI commands,  {n} devices")
    print(f"  SDN          ->  {sdn_time*1000:.2f}ms,  1 command,  1 controller")
    print(f"  Speedup: {trad_time / max(sdn_time, 1e-9):.0f}x faster")
    separator()


if __name__ == "__main__":
    print("\nCSAS3111 Computer Networks -- Live Demo")
    print("Traditional Networking vs SDN")
    demo_failover()
    input("\n  Press Enter to continue to Part 2 (policy deployment)...")
    demo_policy()
    print("\nDemo complete.")
