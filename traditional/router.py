import threading
import time
from simulation.node import Node
from simulation.packet import Packet

INFINITY = 9999
UPDATE_INTERVAL = 5.0                                                 
DEAD_INTERVAL = 30.0                                                               


class TraditionalRouter(Node):
    """RIP-style distance-vector router.

    Routing table format:
        { destination_id: (next_hop_id, distance, last_updated_time) }

    Intentionally does NOT implement split-horizon so count-to-infinity
    shows up naturally in Experiment 5 (failover comparison).
    """

    def __init__(self, node_id: str, update_interval: float = UPDATE_INTERVAL):
        super().__init__(node_id)
        self.update_interval = update_interval
                                                               
        self.routing_table: dict = {
            node_id: (node_id, 0, time.time())
        }
        self._rt_lock = threading.Lock()
        self._neighbor_last_seen: dict = {}                             
        self._running = False
        self._thread: threading.Thread = None
                                                     
        self.on_packet_received = None               
        self.on_route_change = None                                     

                                                                        
               
                                                                        

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False

    def _run_loop(self):
        while self._running:
            self._expire_dead_neighbors()
            self.send_routing_update()
            time.sleep(self.update_interval)

                                                                        
                         
                                                                        

    def add_neighbor(self, neighbor_id: str, link):
        super().add_neighbor(neighbor_id, link)
        with self._rt_lock:
                                                                           
            existing = self.routing_table.get(neighbor_id)
            if existing is None or existing[1] > 1:
                self.routing_table[neighbor_id] = (neighbor_id, 1, time.time())
        self._neighbor_last_seen[neighbor_id] = time.time()

    def _expire_dead_neighbors(self):
        now = time.time()
        dead = [
            n for n, ts in self._neighbor_last_seen.items()
            if now - ts > DEAD_INTERVAL
        ]
        if not dead:
            return
        with self._rt_lock:
            for dead_neighbor in dead:
                                                                     
                for dst, (nh, dist, ts) in list(self.routing_table.items()):
                    if nh == dead_neighbor and dst != self.node_id:
                        del self.routing_table[dst]

                                                                        
                                   
                                                                        

    def send_routing_update(self):
        with self._rt_lock:
            snapshot = {dst: (nh, dist) for dst, (nh, dist, _) in self.routing_table.items()}

        for neighbor_id, link in list(self.neighbors.items()):
            if not link.up:
                continue
            update_pkt = Packet(
                src=self.node_id,
                dst=neighbor_id,
                size_bytes=len(snapshot) * 32,                            
                sent_time=time.time(),
                flow_id="ROUTING_UPDATE",
            )
            update_pkt._routing_table = snapshot                        
            link.transmit(update_pkt, self)

    def receive_routing_update(self, sender_id: str, sender_table: dict):
        self._neighbor_last_seen[sender_id] = time.time()
        changed = False
        with self._rt_lock:
            for dst, (_, dist) in sender_table.items():
                if dst == self.node_id:
                    continue
                new_dist = dist + 1
                if new_dist >= INFINITY:
                    continue
                existing = self.routing_table.get(dst)
                if existing is None or existing[1] > new_dist:
                    old = existing
                    self.routing_table[dst] = (sender_id, new_dist, time.time())
                    changed = True
                    if self.on_route_change and old != self.routing_table[dst]:
                        self.on_route_change(dst, old, self.routing_table[dst])
        return changed

                                                                        
                       
                                                                        

    def receive(self, packet: Packet):
        if packet.flow_id == "ROUTING_UPDATE":
            self._neighbor_last_seen[packet.src] = time.time()
            table = getattr(packet, "_routing_table", {})
            self.receive_routing_update(packet.src, table)
            return

        if packet.dst == self.node_id:
            packet.received_time = time.time()
            packet.path.append(self.node_id)
            if self.on_packet_received:
                self.on_packet_received(packet)
            return

        with self._rt_lock:
            entry = self.routing_table.get(packet.dst)

        if entry is None:
            packet.dropped = True
            return

        next_hop, _, _ = entry
        self._send_on_link(packet, next_hop)

    def send(self, packet: Packet):
        """Inject a packet into the network from this router."""
        self.receive(packet)

                                                                        
                   
                                                                        

    def get_routing_table(self) -> dict:
        with self._rt_lock:
            return {dst: (nh, dist) for dst, (nh, dist, _) in self.routing_table.items()}

    def convergence_complete(self, all_node_ids: list) -> bool:
        """Returns True when this router has a route to every node."""
        with self._rt_lock:
            return all(dst in self.routing_table for dst in all_node_ids)
