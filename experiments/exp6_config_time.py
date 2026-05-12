"""Experiment 6: Configuration time.

Simulates bringing up 20 switches/routers with VLANs, routes, ACLs,
and port security.

Traditional: sequential per-device CLI commands (8 commands × N devices).
SDN: one push to the controller.

Also runs all 10 policy types and measures deployment time for each.
"""

import sys, os, time, csv
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from traditional.network import TraditionalNetwork
from sdn.network import SDNNetwork
from sdn import policies as P
from experiments.metrics import (
    compute_config_time_traditional, compute_config_time_sdn
)

TOPO_20 = os.path.join(os.path.dirname(__file__), "..", "topologies", "topo_20.json")
RESULTS_DIR = os.path.join(os.path.dirname(__file__), "..", "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

COMMANDS_PER_DEVICE = 8
SECONDS_PER_COMMAND = 0.05                          


# simulates typing CLI commands on each device sequentially
def run_traditional_config(n_devices: int) -> dict:
    m = compute_config_time_traditional(
        n_devices,
        commands_per_device=COMMANDS_PER_DEVICE,
        seconds_per_command=SECONDS_PER_COMMAND,
    )
    return m


# simulates a single push to the SDN controller regardless of how many devices there are
def run_sdn_config(n_devices: int) -> dict:
    return compute_config_time_sdn(n_devices)


def run_policy_timing(sdn: SDNNetwork) -> list:
    """Time each of the 10 policies being pushed via the controller."""
    node_ids = sdn.node_ids()
    rows = []

    policy_cases = [
        ("block_subnet",    lambda: P.block_subnet("10.0.1.0/24", "10.0.2.0/24", node_ids)),
        ("rate_limit",      lambda: P.rate_limit("10.0.0.5", 10, node_ids)),
        ("quarantine",      lambda: P.quarantine("10.0.0.99", node_ids)),
        ("voip_path",       lambda: P.voip_path("10.0.1.1", "10.0.2.1", node_ids)),
        ("block_ip",        lambda: P.block_ip("1.2.3.4", node_ids)),
        ("temp_access",     lambda: P.temp_access("10.0.5.50", 24, node_ids)),
        ("mirror_traffic",  lambda: P.mirror_traffic("10.1.0.0/24", "analyzer", node_ids)),
        ("prefer_wired",    lambda: P.prefer_wired("10.0.0.0/24", node_ids)),
        ("drop_guest_wknd", lambda: P.drop_guest_weekend("guest_vlan", node_ids)),
        ("add_vlan",        lambda: P.add_vlan(100, "ResearchWing", node_ids)),
    ]

    for name, make_policy in policy_cases:
        policy_dict, cli_cmds = make_policy()
        n_devices = len(node_ids)
        n_cli_lines = sum(cmd.count("\n") + 1 for cmd in cli_cmds)

                                                         
        t_trad_start = time.perf_counter()
        time.sleep(SECONDS_PER_COMMAND * n_devices * 3)                                  
        t_trad = time.perf_counter() - t_trad_start

                                  
        t_sdn = sdn.controller.policy_deployment_time(policy_dict)

        rows.append({
            "policy": name,
            "n_devices": n_devices,
            "trad_devices_touched": n_devices,
            "trad_cli_lines": n_cli_lines,
            "trad_time_s": round(t_trad, 4),
            "sdn_devices_touched": 1,
            "sdn_cli_lines": 1,
            "sdn_time_s": round(t_sdn, 6),
            "speedup_x": round(t_trad / max(t_sdn, 1e-9), 1),
        })
        print(f"  {name:20s}  trad={t_trad:.3f}s  sdn={t_sdn*1000:.2f}ms  "
              f"speedup={rows[-1]['speedup_x']}x")

    return rows


def main():
    print("\n=== Experiment 6: Configuration time ===")

    sdn = SDNNetwork(TOPO_20)
    node_ids = sdn.node_ids()
    n = len(node_ids)

    print(f"\n[Config] Network size: {n} devices")

    trad_cfg = run_traditional_config(n)
    sdn_cfg = run_sdn_config(n)

    print(f"  Traditional: {n} devices × {COMMANDS_PER_DEVICE} cmds × "
          f"{SECONDS_PER_COMMAND}s = {trad_cfg['config_time_s']:.1f}s total")
    print(f"  SDN:         1 controller push = {sdn_cfg['config_time_s']*1000:.1f}ms total")

                              
    cfg_path = os.path.join(RESULTS_DIR, "exp6_config_time.csv")
    with open(cfg_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["approach", "devices", "commands", "config_time_s"])
        w.writerow(["traditional", trad_cfg["devices_touched"],
                    trad_cfg["total_commands"], trad_cfg["config_time_s"]])
        w.writerow(["sdn", sdn_cfg["devices_touched"],
                    sdn_cfg["total_commands"], sdn_cfg["config_time_s"]])
    print(f"  Saved {cfg_path}")

    print("\n[Policy Deployment Timing]")
    policy_rows = run_policy_timing(sdn)
    pol_path = os.path.join(RESULTS_DIR, "exp6_policies.csv")
    with open(pol_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=policy_rows[0].keys())
        writer.writeheader()
        writer.writerows(policy_rows)
    print(f"  Saved {pol_path}")


if __name__ == "__main__":
    main()
