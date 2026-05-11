import threading
import time

try:
    import networkx as nx
except ImportError:
    raise ImportError("networkx is required: pip install networkx")


class SDNController:
    """Centralized SDN controller.

    Holds a global NetworkX graph, computes shortest paths via Dijkstra,
    and pushes flow rules to every switch.  When a link fails the controller
    recomputes and pushes updated rules within a single function call —
    this is the key performance advantage over distance-vector.
    """

    def __init__(self):
        self.graph = nx.Graph()
        self.switches: dict = {}                                  
        self.policies: list = []
        self._lock = threading.Lock()
        self.alive = True
                       
        self.last_recompute_time: float = 0.0                                            

                                                                        
                         
                                                                        

    def register_switch(self, switch):
        with self._lock:
            self.switches[switch.node_id] = switch
            self.graph.add_node(switch.node_id)

    def add_link(self, a: str, b: str, weight: float = 1.0, **attrs):
        with self._lock:
            self.graph.add_edge(a, b, weight=weight, **attrs)

    def remove_link(self, a: str, b: str):
        with self._lock:
            if self.graph.has_edge(a, b):
                self.graph.remove_edge(a, b)

                                                                        
                      
                                                                        

    def compute_path(self, src: str, dst: str) -> list | None:
        with self._lock:
            try:
                return nx.shortest_path(self.graph, src, dst, weight="weight")
            except (nx.NetworkXNoPath, nx.NodeNotFound):
                return None

    def install_flow(self, src: str, dst: str) -> bool:
        """Compute path src->dst and install per-hop rules in every switch."""
        path = self.compute_path(src, dst)
        if path is None:
            return False
        for i, sw_id in enumerate(path[:-1]):
            next_hop = path[i + 1]
            sw = self.switches.get(sw_id)
            if sw:
                sw.install_rule(dst, next_hop)
        return True

                                                                        
                                         
                                                                        

    def link_failure(self, a: str, b: str):
        if not self.alive:
            return
        t0 = time.perf_counter()
        self.remove_link(a, b)

                                                                       
        affected: set = set()
        with self._lock:
            for sw_id, sw in self.switches.items():
                for dst, next_hop in list(sw.flow_table.items()):
                                                                                      
                                                             
                    if (sw_id == a and next_hop == b) or (sw_id == b and next_hop == a):
                        affected.add((sw_id, dst))

                                         
        for sw_id, sw in self.switches.items():
            sw.clear_flow_table()

                                                          
        with self._lock:
            all_ids = list(self.switches.keys())
        for src in all_ids:
            for dst in all_ids:
                if src != dst:
                    self.install_flow(src, dst)

        self.last_recompute_time = time.perf_counter() - t0

    def link_restored(self, a: str, b: str, weight: float = 1.0):
        if not self.alive:
            return
        self.add_link(a, b, weight=weight)
                                                       
        with self._lock:
            all_ids = list(self.switches.keys())
        for src in all_ids:
            for dst in all_ids:
                if src != dst:
                    self.install_flow(src, dst)

                                                                        
                   
                                                                        

    def add_policy(self, policy: dict):
        """Apply a named policy to the network.

        Supported policy types (see policies.py for helpers):
          block_subnet, rate_limit, quarantine, voip_path,
          block_ip, temp_access, mirror, prefer_wired,
          drop_guest_weekend, add_vlan
        """
        self.policies.append(policy)
        ptype = policy.get("type")
        handler = getattr(self, f"_policy_{ptype}", None)
        if handler:
            handler(policy)

    def _policy_block_subnet(self, policy: dict):
        src_subnet = policy["src"]
        dst_subnet = policy["dst"]
        for sw in self.switches.values():
            sw.add_acl("block", src_subnet, dst_subnet)

    def _policy_quarantine(self, policy: dict):
        host = policy["host"]
        for sw in self.switches.values():
            sw.add_acl("block", host, "*")
            sw.add_acl("block", "*", host)

    def _policy_block_ip(self, policy: dict):
        ip = policy["ip"]
        for sw in self.switches.values():
            sw.add_acl("block", "*", ip)

    def _policy_rate_limit(self, policy: dict):
        host = policy["host"]
        mbps = policy["mbps"]
        for sw in self.switches.values():
            sw.add_rate_limit(host, mbps)

                                                               
    def _policy_voip_path(self, p): pass
    def _policy_temp_access(self, p): pass
    def _policy_mirror(self, p): pass
    def _policy_prefer_wired(self, p): pass
    def _policy_drop_guest_weekend(self, p): pass
    def _policy_add_vlan(self, p): pass

                                                                        
                        
                                                                        

    def kill(self):
        """Simulate controller failure — switches can no longer get new rules."""
        self.alive = False

    def revive(self):
        self.alive = True

    def policy_deployment_time(self, policy: dict) -> float:
        """Return seconds taken to push a policy to all switches."""
        t0 = time.perf_counter()
        self.add_policy(policy)
        return time.perf_counter() - t0
