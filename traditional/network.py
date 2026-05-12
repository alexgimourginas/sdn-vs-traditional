import json
import time
from simulation.link import Link
from .router import TraditionalRouter


class TraditionalNetwork:
    """Builds and manages a traditional distance-vector network from a topology JSON."""

    def __init__(self, topology_path: str, update_interval: float = 5.0):
        self.routers: dict[str, TraditionalRouter] = {}
        self.links: list[Link] = []
        self.link_index: dict[tuple, Link] = {}                                     
        self._update_interval = update_interval
        self._load(topology_path)

    def _load(self, path: str):
        with open(path) as f:
            topo = json.load(f)

        for node_id in topo["nodes"]:
            self.routers[node_id] = TraditionalRouter(node_id, self._update_interval)

        for edge in topo["edges"]:
            a_id, b_id = edge["a"], edge["b"]
            router_a = self.routers[a_id]
            router_b = self.routers[b_id]
            delay_ms = edge.get("delay_ms", 5)
            link = Link(
                router_a, router_b,
                bandwidth_mbps=edge.get("bandwidth_mbps", 100),
                delay_ms=delay_ms,
                loss_rate=edge.get("loss_rate", 0.0),
                jitter_ms=delay_ms * 0.5,
            )
            router_a.add_neighbor(b_id, link)
            router_b.add_neighbor(a_id, link)
            self.links.append(link)
            key = (min(a_id, b_id), max(a_id, b_id))
            self.link_index[key] = link

    def start(self):
        for router in self.routers.values():
            router.start()

    def stop(self):
        for router in self.routers.values():
            router.stop()

    def wait_for_convergence(self, timeout: float = 60.0) -> float:
        """Block until all routers know routes to all other routers.

        Returns the actual elapsed seconds, or raises TimeoutError.
        """
        all_ids = list(self.routers.keys())
        start = time.time()
        while time.time() - start < timeout:
            if all(r.convergence_complete(all_ids) for r in self.routers.values()):
                return time.time() - start
            time.sleep(0.1)
        raise TimeoutError(f"Traditional network did not converge within {timeout}s")

    def get_link(self, a: str, b: str) -> Link:
        key = (min(a, b), max(a, b))
        return self.link_index.get(key)

    def fail_link(self, a: str, b: str):
        link = self.get_link(a, b)
        if link:
            link.fail()

    def restore_link(self, a: str, b: str):
        link = self.get_link(a, b)
        if link:
            link.restore()

    def fail_node(self, node_id: str):
        router = self.routers.get(node_id)
        if router:
            router.stop()
            for link in router.neighbors.values():
                link.fail()

    def node_ids(self) -> list:
        return list(self.routers.keys())

    def __repr__(self):
        return f"TraditionalNetwork({len(self.routers)} routers, {len(self.links)} links)"
