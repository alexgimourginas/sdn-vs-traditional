# Traditional vs SDN Network Performance Comparison
CSAS3111 Computer Networks - Spring 2026 Final Project

## Setup

```bash
pip install -r requirements.txt
```

Python 3.10+ required.

## Project Structure

```
simulation/       Packet, Link, Node, Scheduler, Logger
traditional/      Distance-vector (RIP-style) router and network builder
sdn/              SDN controller, switch, and policies
experiments/      Traffic generator, failure injector, metrics, experiment scripts
topologies/       JSON topology files for 5, 10, 20, 50, and 100 nodes
results/          CSV output from experiments
graphs/           PNG charts and report_gen.py
```

## Running Experiments

Run from the project root. Each script saves CSVs to results/.

```bash
python experiments/exp1_throughput.py
python experiments/exp2_latency.py
python experiments/exp3_jitter.py
python experiments/exp4_packet_loss.py
python experiments/exp5_failover.py
python experiments/exp6_config_time.py
python experiments/exp7_scalability.py
```

After all experiments finish, generate the graphs:

```bash
python graphs/report_gen.py
```

## How It Works

### Traditional Network

Each router runs a background thread that broadcasts its routing table to neighbors every 5 seconds. Routers update their tables based on what neighbors report. When a link goes down the news spreads slowly hop by hop, which is why recovery takes 15-30 seconds. No router has a full picture of the network.

### SDN Network

One controller holds a complete graph of the topology and computes shortest paths using Dijkstra. Switches just forward packets according to rules the controller pushes to them. When a link fails the controller recomputes all paths and updates every switch in one call, which takes milliseconds. All 10 policies (block, quarantine, rate-limit, etc.) are applied through the controller and pushed out automatically.

### Simulation Engine

Packet, Link, Node, Scheduler, and Logger are the building blocks both networks run on. Links have configurable delay, bandwidth, and packet loss. Everything gets timestamped and written to CSV for analysis.

## Results Summary

| Metric | Traditional | SDN |
|---|---|---|
| Failover recovery | 15-30 s | under 1 s |
| Policy deployment | minutes | milliseconds |
| Configuration (20 devices) | ~80 s | under 1 s |
| Tail latency under congestion | higher | lower |
| Controller as single point of failure | N/A | Yes |

## Topology Format

```json
{
  "nodes": ["R0", "R1"],
  "edges": [
    {"a": "R0", "b": "R1", "bandwidth_mbps": 100, "delay_ms": 5, "loss_rate": 0.0}
  ]
}
```

To regenerate topologies: `python topologies/gen_topologies.py`

## Dependencies

| Library | Version |
|---|---|
| networkx | 3.3 |
| matplotlib | 3.9.0 |
| pandas | 2.2.2 |
| numpy | 1.26.4 |
