"""Generate topology JSON files for 5, 10, 20, 50, 100 nodes.

Each topology is a connected graph where nodes are routers/switches and
edges carry bandwidth/delay/loss metadata.

Run once:  python topologies/gen_topologies.py
"""

import json
import random
import os

random.seed(42)


def make_topology(n: int, extra_edges_factor: float = 0.3) -> dict:
    """Build a random connected topology with n nodes.

    Strategy:
      1. Create a spanning chain (ring) to guarantee connectivity.
      2. Add extra random edges for redundancy (failover paths).
    """
    nodes = [f"R{i}" for i in range(n)]

                    
    edges = []
    for i in range(n - 1):
        edges.append(_make_edge(nodes[i], nodes[i + 1]))

                                                 
    if n > 2:
        edges.append(_make_edge(nodes[-1], nodes[0]))

                        
    extra = int(n * extra_edges_factor)
    existing = {(e["a"], e["b"]) for e in edges}
    attempts = 0
    added = 0
    while added < extra and attempts < extra * 10:
        a, b = random.sample(nodes, 2)
        if a > b:
            a, b = b, a
        if (a, b) not in existing:
            edges.append(_make_edge(a, b))
            existing.add((a, b))
            added += 1
        attempts += 1

    return {"nodes": nodes, "edges": edges}


def _make_edge(a: str, b: str) -> dict:
    return {
        "a": a,
        "b": b,
        "bandwidth_mbps": random.choice([100, 100, 100, 1000]),
        "delay_ms": random.randint(1, 20),
        "loss_rate": random.choice([0.0, 0.0, 0.0, 0.001]),
    }


if __name__ == "__main__":
    out_dir = os.path.dirname(__file__)
    for n in [5, 10, 20, 50, 100]:
        topo = make_topology(n)
        path = os.path.join(out_dir, f"topo_{n}.json")
        with open(path, "w") as f:
            json.dump(topo, f, indent=2)
        print(f"Wrote {path}  ({len(topo['nodes'])} nodes, {len(topo['edges'])} edges)")
