import random
import threading


class Link:
    """Bidirectional link between two nodes with bandwidth, delay, and loss."""

    def __init__(self, node_a, node_b, bandwidth_mbps=100, delay_ms=5, loss_rate=0.0,
                 jitter_ms=0.0, max_queue=0):
        self.node_a = node_a
        self.node_b = node_b
        self.bandwidth_mbps = bandwidth_mbps
        self.delay_ms = delay_ms
        self.loss_rate = loss_rate
        self.jitter_ms = jitter_ms
        self.max_queue = max_queue  # 0 = unlimited
        self._in_flight = 0
        self.up = True
        self._lock = threading.Lock()

    def transmit(self, packet, from_node, priority_bypass=False):
        with self._lock:
            if not self.up:
                packet.dropped = True
                return
            if random.random() < self.loss_rate:
                packet.dropped = True
                return
            if not priority_bypass and self.max_queue > 0 and self._in_flight >= self.max_queue:
                packet.dropped = True
                return
            self._in_flight += 1

        target = self.node_b if from_node is self.node_a else self.node_a
        delay_sec = self.delay_ms / 1000.0
        if self.jitter_ms > 0:
            delay_sec = max(0.0, delay_sec + random.uniform(-self.jitter_ms, self.jitter_ms) / 1000.0)

        def _deliver():
            with self._lock:
                self._in_flight -= 1
            target.receive(packet)

        threading.Timer(delay_sec, _deliver).start()

    def fail(self):
        with self._lock:
            self.up = False

    def restore(self):
        with self._lock:
            self.up = True

    def set_loss_rate(self, rate: float):
        with self._lock:
            self.loss_rate = max(0.0, min(1.0, rate))

    def __repr__(self):
        status = "UP" if self.up else "DOWN"
        return (f"Link({self.node_a.node_id}<->{self.node_b.node_id} "
                f"{self.bandwidth_mbps}Mbps {self.delay_ms}ms loss={self.loss_rate:.2%} {status})")
