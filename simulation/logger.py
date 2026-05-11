import csv
import json
import os
import threading
from simulation.packet import Packet


class Logger:
    """Thread-safe logger. Writes per-packet records to CSV and events to JSON."""

    PACKET_FIELDS = [
        "flow_id", "src", "dst", "size_bytes", "priority",
        "sent_time", "received_time", "latency_s", "dropped",
        "path", "hop_count",
    ]

    def __init__(self, results_dir: str = "results"):
        self._results_dir = results_dir
        os.makedirs(results_dir, exist_ok=True)
        self._lock = threading.Lock()
        self._packet_writers: dict = {}                                              
        self._event_logs: dict = {}                                      

    def _get_packet_writer(self, experiment: str):
        if experiment not in self._packet_writers:
            path = os.path.join(self._results_dir, f"{experiment}_packets.csv")
            f = open(path, "w", newline="")
            writer = csv.DictWriter(f, fieldnames=self.PACKET_FIELDS)
            writer.writeheader()
            self._packet_writers[experiment] = (f, writer)
        return self._packet_writers[experiment][1]

    def log_packet(self, experiment: str, packet: Packet):
        with self._lock:
            writer = self._get_packet_writer(experiment)
            writer.writerow({
                "flow_id": packet.flow_id,
                "src": packet.src,
                "dst": packet.dst,
                "size_bytes": packet.size_bytes,
                "priority": packet.priority,
                "sent_time": f"{packet.sent_time:.6f}",
                "received_time": f"{packet.received_time:.6f}" if packet.received_time is not None else "",
                "latency_s": f"{packet.latency():.6f}" if packet.latency() is not None else "",
                "dropped": packet.dropped,
                "path": "->".join(packet.path),
                "hop_count": len(packet.path),
            })

    def log_event(self, experiment: str, sim_time: float, event_type: str, detail: dict = None):
        with self._lock:
            if experiment not in self._event_logs:
                self._event_logs[experiment] = []
            self._event_logs[experiment].append({
                "sim_time": sim_time,
                "event": event_type,
                "detail": detail or {},
            })

    def flush(self, experiment: str = None):
        with self._lock:
            targets = [experiment] if experiment else list(self._packet_writers.keys())
            for exp in targets:
                if exp in self._packet_writers:
                    self._packet_writers[exp][0].flush()
                              
            for exp, events in self._event_logs.items():
                if experiment and exp != experiment:
                    continue
                path = os.path.join(self._results_dir, f"{exp}_events.json")
                with open(path, "w") as f:
                    json.dump(events, f, indent=2)

    def close(self):
        self.flush()
        with self._lock:
            for f, _ in self._packet_writers.values():
                f.close()
            self._packet_writers.clear()
