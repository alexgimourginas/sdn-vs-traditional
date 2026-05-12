import time
import threading
from simulation.node import Node
from simulation.packet import Packet


class SDNSwitch(Node):
    """Thin SDN switch.

    Maintains a flow table pushed by the controller.  On a table miss it
    calls back to the controller (packet-in), installs the returned rule,
    then forwards.  If the controller is dead the packet is dropped.
    """

    def __init__(self, switch_id: str, controller):
        super().__init__(switch_id)
        self.controller = controller
        self.flow_table: dict = {}                              
        self._acls: list = []                                                           
        self._rate_limits: dict = {}                                                         
        self._lock = threading.Lock()
        self.on_packet_received = None                                   
        controller.register_switch(self)

                                                                        
                           
                                                                        

    def install_rule(self, dst: str, next_hop: str):
        with self._lock:
            self.flow_table[dst] = next_hop

    def clear_flow_table(self):
        with self._lock:
            self.flow_table.clear()

    def add_acl(self, action: str, src_pattern: str, dst_pattern: str):
        with self._lock:
            self._acls.append((action, src_pattern, dst_pattern))

    def add_rate_limit(self, host: str, mbps: float):
        with self._lock:
            self._rate_limits[host] = mbps

                                                                        
               
                                                                        

    def _acl_drop(self, packet: Packet) -> bool:
        with self._lock:
            acls = list(self._acls)
        for action, src_pat, dst_pat in acls:
            src_match = src_pat in ("*", packet.src)
            dst_match = dst_pat in ("*", packet.dst)
            if src_match and dst_match and action == "block":
                return True
        return False

                                                                        
                       
                                                                        

    def receive(self, packet: Packet):
        arrival_time = time.time()

        if self._acl_drop(packet):
            packet.dropped = True
            return

        if packet.dst == self.node_id:
            packet.received_time = arrival_time
            packet.path.append(self.node_id)
            if self.on_packet_received:
                self.on_packet_received(packet)
            return

        with self._lock:
            next_hop = self.flow_table.get(packet.dst)

        if next_hop is None:
                                           
            if not self.controller.alive:
                packet.dropped = True
                return
            installed = self.controller.install_flow(self.node_id, packet.dst)
            if not installed:
                packet.dropped = True
                return
            with self._lock:
                next_hop = self.flow_table.get(packet.dst)
            if next_hop is None:
                packet.dropped = True
                return

        self._send_on_link(packet, next_hop)

    def send(self, packet: Packet):
        """Inject a packet into the network from this switch."""
        self.receive(packet)
