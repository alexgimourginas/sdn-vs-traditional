"""Module 9: Report generator.

Reads CSVs from results/ and produces publication-quality PNGs in graphs/.
Run after all experiments have produced their CSV files:
    python graphs/report_gen.py
"""

import os
import sys
import csv
import math

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.ticker as mticker
    import numpy as np
except ImportError:
    raise ImportError("pip install matplotlib numpy")

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "..", "results")
GRAPHS_DIR = os.path.dirname(__file__)

TRAD_COLOR = "#E05C5C"
SDN_COLOR  = "#4A90D9"
STYLE = {
    "font.family": "DejaVu Sans",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.alpha": 0.35,
    "figure.dpi": 150,
}
plt.rcParams.update(STYLE)


                                                                    
         
                                                                    

def _load(filename: str) -> list[dict]:
    path = os.path.join(RESULTS_DIR, filename)
    if not os.path.exists(path):
        print(f"  [skip] {filename} not found — run the experiment first.")
        return []
    with open(path) as f:
        return list(csv.DictReader(f))


def _save(fig, name: str):
    path = os.path.join(GRAPHS_DIR, name)
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved {path}")


def _flt(row: dict, key: str, default=0.0):
    v = row.get(key, default)
    try:
        return float(v)
    except (ValueError, TypeError):
        return default


                                                                    
                           
                                                                    

def plot_exp1():
    trad = _load("exp1_throughput_traditional.csv")
    sdn  = _load("exp1_throughput_sdn.csv")
    if not trad and not sdn:
        return

    fig, ax = plt.subplots(figsize=(7, 4.5))

    if trad:
        x = [_flt(r, "offered_mbps") for r in trad]
        y = [_flt(r, "throughput_mbps") for r in trad]
        ax.plot(x, y, "o-", color=TRAD_COLOR, label="Traditional", linewidth=2)

    if sdn:
        x = [_flt(r, "offered_mbps") for r in sdn]
        y = [_flt(r, "throughput_mbps") for r in sdn]
        ax.plot(x, y, "s-", color=SDN_COLOR, label="SDN", linewidth=2)

                    
    if trad or sdn:
        all_x = ([_flt(r, "offered_mbps") for r in trad] +
                 [_flt(r, "offered_mbps") for r in sdn])
        lim = max(all_x) * 1.05
        ax.plot([0, lim], [0, lim], "--", color="grey", alpha=0.5, label="Ideal (1:1)")
        ax.set_xlim(0, lim)
        ax.set_ylim(0, lim)

    ax.set_xlabel("Offered Load (Mbps)")
    ax.set_ylabel("Delivered Throughput (Mbps)")
    ax.set_title("Experiment 1: Throughput Under Increasing Load")
    ax.legend()
    _save(fig, "exp1_throughput.png")


                                                                    
                                  
                                                                    

def plot_exp2():
    trad = _load("exp2_latency_traditional.csv")
    sdn  = _load("exp2_latency_sdn.csv")
    if not trad and not sdn:
        return

    keys = ["latency_avg_ms", "latency_median_ms", "latency_p95_ms", "latency_p99_ms"]
    labels = ["Mean", "Median (p50)", "p95", "p99"]
    x = range(len(labels))
    width = 0.35

    fig, ax = plt.subplots(figsize=(7, 4.5))

    if trad:
        vals = [_flt(trad[0], k) for k in keys]
        ax.bar([i - width/2 for i in x], vals, width, label="Traditional", color=TRAD_COLOR)
    if sdn:
        vals = [_flt(sdn[0], k) for k in keys]
        ax.bar([i + width/2 for i in x], vals, width, label="SDN", color=SDN_COLOR)

    ax.set_xticks(list(x))
    ax.set_xticklabels(labels)
    ax.set_ylabel("Latency (ms)")
    ax.set_title("Experiment 2: Latency Percentiles Under Congestion")
    ax.legend()
    _save(fig, "exp2_latency.png")


                                                                    
                                 
                                                                    

def plot_exp3():
    trad = _load("exp3_jitter_traditional.csv")
    sdn  = _load("exp3_jitter_sdn.csv")
    if not trad and not sdn:
        return

    fig, ax = plt.subplots(figsize=(5, 4))
    vals, cols, lbls = [], [], []
    if trad:
        vals.append(_flt(trad[0], "jitter_ms"))
        cols.append(TRAD_COLOR); lbls.append("Traditional")
    if sdn:
        vals.append(_flt(sdn[0], "jitter_ms"))
        cols.append(SDN_COLOR); lbls.append("SDN")

    bars = ax.bar(lbls, vals, color=cols, width=0.45)
    for bar, v in zip(bars, vals):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01,
                f"{v:.3f} ms", ha="center", va="bottom", fontsize=9)

    ax.set_ylabel("Jitter — StdDev of inter-arrival time (ms)")
    ax.set_title("Experiment 3: Jitter (VoIP / Video Quality)")
    _save(fig, "exp3_jitter.png")


                                                                    
                                      
                                                                    

def plot_exp4():
    trad = _load("exp4_packet_loss_traditional.csv")
    sdn  = _load("exp4_packet_loss_sdn.csv")
    if not trad and not sdn:
        return

    fig, ax = plt.subplots(figsize=(5, 4))
    vals, cols, lbls = [], [], []
    if trad:
        vals.append(_flt(trad[0], "packet_loss_pct"))
        cols.append(TRAD_COLOR); lbls.append("Traditional")
    if sdn:
        vals.append(_flt(sdn[0], "packet_loss_pct"))
        cols.append(SDN_COLOR); lbls.append("SDN")

    bars = ax.bar(lbls, vals, color=cols, width=0.45)
    for bar, v in zip(bars, vals):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.3,
                f"{v:.1f}%", ha="center", va="bottom", fontsize=9)

    ax.set_ylabel("Legitimate Packet Loss (%)")
    ax.set_title("Experiment 4: Packet Loss Under DDoS-like Attack")
    _save(fig, "exp4_packet_loss.png")


                                                                    
                                        
                                                                    

def plot_exp5():
    rows = _load("exp5_failover.csv")
    if not rows:
        return

    fig, ax = plt.subplots(figsize=(5, 4))
    for row in rows:
        label = row.get("label", "?")
        rt = _flt(row, "recovery_time_s")
        color = TRAD_COLOR if "trad" in label else SDN_COLOR
        bar = ax.bar(label.capitalize(), rt, color=color, width=0.45)
        ax.text(bar[0].get_x() + bar[0].get_width()/2,
                bar[0].get_height() + 0.05,
                f"{rt:.3f}s", ha="center", va="bottom", fontsize=9)

    ax.set_ylabel("Recovery Time (seconds)")
    ax.set_title("Experiment 5: Failover Recovery Time\n(lower is better)")
    _save(fig, "exp5_failover.png")


                                                                    
                                                
                                                                    

def plot_exp6():
    cfg = _load("exp6_config_time.csv")
    pol = _load("exp6_policies.csv")

    if cfg:
        fig, ax = plt.subplots(figsize=(5, 4))
        for row in cfg:
            color = TRAD_COLOR if row["approach"] == "traditional" else SDN_COLOR
            t = _flt(row, "config_time_s")
            bar = ax.bar(row["approach"].capitalize(), t, color=color, width=0.45)
            ax.text(bar[0].get_x() + bar[0].get_width()/2,
                    bar[0].get_height() + 0.5,
                    f"{t:.1f}s", ha="center", va="bottom", fontsize=9)
        ax.set_ylabel("Total Configuration Time (seconds)")
        ax.set_title("Experiment 6: Network Configuration Time")
        _save(fig, "exp6_config_time.png")

    if pol:
        names = [r["policy"] for r in pol]
        trad_t = [_flt(r, "trad_time_s") for r in pol]
        sdn_t  = [_flt(r, "sdn_time_s") for r in pol]
        x = range(len(names))
        width = 0.35

        fig, ax = plt.subplots(figsize=(10, 4.5))
        ax.bar([i - width/2 for i in x], trad_t, width, label="Traditional", color=TRAD_COLOR)
        ax.bar([i + width/2 for i in x], sdn_t,  width, label="SDN", color=SDN_COLOR)
        ax.set_xticks(list(x))
        ax.set_xticklabels(names, rotation=30, ha="right", fontsize=8)
        ax.set_ylabel("Policy Deployment Time (seconds)")
        ax.set_title("Experiment 6: Policy Deployment Time per Policy Type")
        ax.legend()
        _save(fig, "exp6_policies.png")


                                                                    
                                        
                                                                    

def plot_exp7():
    trad = _load("exp7_scalability_traditional.csv")
    sdn  = _load("exp7_scalability_sdn.csv")
    if not trad and not sdn:
        return

    metrics = [
        ("convergence_s",    "Convergence / Setup Time (s)", "Exp 7a: Convergence vs Network Size"),
        ("throughput_mbps",  "Throughput (Mbps)",            "Exp 7b: Throughput vs Network Size"),
        ("recovery_time_s",  "Failover Recovery Time (s)",   "Exp 7c: Recovery Time vs Network Size"),
    ]

    for key, ylabel, title in metrics:
        fig, ax = plt.subplots(figsize=(6, 4))
        if trad:
            x = [_flt(r, "n_nodes") for r in trad]
            y = [_flt(r, key) for r in trad]
            ax.plot(x, y, "o-", color=TRAD_COLOR, label="Traditional", linewidth=2)
        if sdn:
            x = [_flt(r, "n_nodes") for r in sdn]
            y = [_flt(r, key) for r in sdn]
            ax.plot(x, y, "s-", color=SDN_COLOR, label="SDN", linewidth=2)
        ax.set_xlabel("Network Size (nodes)")
        ax.set_ylabel(ylabel)
        ax.set_title(title)
        ax.legend()
        fname = f"exp7_{key}.png"
        _save(fig, fname)


                                                                    
      
                                                                    

def main():
    print("\n=== Generating graphs from results/ ===\n")
    plot_exp1()
    plot_exp2()
    plot_exp3()
    plot_exp4()
    plot_exp5()
    plot_exp6()
    plot_exp7()
    print("\nAll graphs written to graphs/")


if __name__ == "__main__":
    main()
