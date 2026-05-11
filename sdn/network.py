import json
from simulation.link import Link
from .controller import SDNController
from .switch import SDNSwitch


class SDNNetwork:
    """Builds and manages an SDN network from a topology JSON."""

    def __init__(self, topology_path: str):
        self.controller = SDNController()
        self.switches: dict[str, SDNSwitch] = {}
        self.links: list[Link] = []
        self.link_index: dict[tuple, Link] = {}
        self._load(topology_path)

    def _load(self, path: str):
        with open(path) as f:
            topo = json.load(f)

        for node_id in topo["nodes"]:
            sw = SDNSwitch(node_id, self.controller)
            self.switches[node_id] = sw

        for edge in topo["edges"]:
            a_id, b_id = edge["a"], edge["b"]
            sw_a = self.switches[a_id]
            sw_b = self.switches[b_id]
            delay_ms = edge.get("delay_ms", 5)
            link = Link(
                sw_a, sw_b,
                bandwidth_mbps=edge.get("bandwidth_mbps", 100),
                delay_ms=delay_ms,
                loss_rate=edge.get("loss_rate", 0.0),
            )
            sw_a.add_neighbor(b_id, link)
            sw_b.add_neighbor(a_id, link)
            self.links.append(link)
            weight = delay_ms / 10.0                                          
            self.controller.add_link(a_id, b_id, weight=weight)
            key = (min(a_id, b_id), max(a_id, b_id))
            self.link_index[key] = link

                                                                                 
        self._install_all_flows()

    def _install_all_flows(self):
        ids = list(self.switches.keys())
        for src in ids:
            for dst in ids:
                if src != dst:
                    self.controller.install_flow(src, dst)

    def get_link(self, a: str, b: str) -> Link:
        key = (min(a, b), max(a, b))
        return self.link_index.get(key)

    def fail_link(self, a: str, b: str):
        link = self.get_link(a, b)
        if link:
            link.fail()
        self.controller.link_failure(a, b)

    def restore_link(self, a: str, b: str):
        link = self.get_link(a, b)
        if link:
            link.restore()
        self.controller.link_restored(a, b)

    def fail_node(self, node_id: str):
        sw = self.switches.get(node_id)
        if sw:
            for link in sw.neighbors.values():
                link.fail()

    def fail_controller(self):
        self.controller.kill()

    def revive_controller(self):
        self.controller.revive()

    def node_ids(self) -> list:
        return list(self.switches.keys())

    def __repr__(self):
        return f"SDNNetwork({len(self.switches)} switches, {len(self.links)} links)"
