import threading
from simulation.packet import Packet


class Node:
    """Base class for any network node (router or switch).

    Subclasses override `receive` to implement forwarding logic.
    """

    def __init__(self, node_id: str):
        self.node_id = node_id
        self.neighbors: dict = {}                        
        self._lock = threading.Lock()

    def add_neighbor(self, neighbor_id: str, link):
        with self._lock:
            self.neighbors[neighbor_id] = link

    def remove_neighbor(self, neighbor_id: str):
        with self._lock:
            self.neighbors.pop(neighbor_id, None)

    def receive(self, packet: Packet):
        """Called by a Link when a packet arrives. Override in subclasses."""
        raise NotImplementedError

    def _send_on_link(self, packet: Packet, next_hop_id: str):
        link = self.neighbors.get(next_hop_id)
        if link is None:
            packet.dropped = True
            return
        packet.path.append(self.node_id)
        link.transmit(packet, self)

    def __repr__(self):
        return f"{self.__class__.__name__}({self.node_id})"
