"""The 10 sample policies from Module 7.

Each function returns a policy dict that SDNController.add_policy() understands.
For traditional networks, each function also returns a list of simulated CLI
commands (one per device) so we can count device-touches and CLI lines.
"""


def block_subnet(src: str, dst: str, devices: list) -> tuple[dict, list]:
    policy = {"type": "block_subnet", "src": src, "dst": dst}
    cli = [f"ip access-list extended BLOCK_{src}_to_{dst}\n  deny ip {src} {dst} any\n  permit ip any any\ninterface all\n  ip access-group BLOCK_{src}_to_{dst} in"
           for _ in devices]
    return policy, cli


def rate_limit(host: str, mbps: float, devices: list) -> tuple[dict, list]:
    policy = {"type": "rate_limit", "host": host, "mbps": mbps}
    cli = [f"policy-map RATE_{host}\n  class class-default\n    police rate {int(mbps)}m\ninterface all\n  service-policy input RATE_{host}"
           for _ in devices]
    return policy, cli


def quarantine(host: str, devices: list) -> tuple[dict, list]:
    policy = {"type": "quarantine", "host": host}
    cli = [f"ip access-list extended QUARANTINE_{host}\n  deny ip host {host} any\n  deny ip any host {host}\n  permit ip any any\ninterface all\n  ip access-group QUARANTINE_{host} in"
           for _ in devices]
    return policy, cli


def voip_path(src: str, dst: str, devices: list) -> tuple[dict, list]:
    policy = {"type": "voip_path", "src": src, "dst": dst}
    cli = [f"ip access-list extended VOIP\n  permit udp host {src} host {dst} range 16384 32767\nroute-map VOIP_LL permit 10\n  match ip address VOIP\n  set ip next-hop <low-latency-hop>"
           for _ in devices]
    return policy, cli


def block_ip(ip: str, devices: list) -> tuple[dict, list]:
    policy = {"type": "block_ip", "ip": ip}
    cli = [f"ip access-list extended BLOCK_MALICIOUS\n  deny ip any host {ip}\ninterface all\n  ip access-group BLOCK_MALICIOUS in"
           for _ in devices]
    return policy, cli


def temp_access(host: str, hours: int, devices: list) -> tuple[dict, list]:
    policy = {"type": "temp_access", "host": host, "hours": hours}
    cli = [f"ip access-list extended TEMP_{host}\n  permit ip host {host} any time-range TEMP_{hours}H\ntime-range TEMP_{hours}H\n  duration {hours * 3600}"
           for _ in devices]
    return policy, cli


def mirror_traffic(src_subnet: str, analyzer: str, devices: list) -> tuple[dict, list]:
    policy = {"type": "mirror", "src_subnet": src_subnet, "analyzer": analyzer}
    cli = [f"monitor session 1 source interface all\nmonitor session 1 destination interface {analyzer}\nip access-list extended MIRROR_{src_subnet}\n  permit ip {src_subnet} any"
           for _ in devices]
    return policy, cli


def prefer_wired(src_subnet: str, devices: list) -> tuple[dict, list]:
    policy = {"type": "prefer_wired", "src_subnet": src_subnet}
    cli = [f"route-map PREFER_WIRED permit 10\n  match interface GigabitEthernet\n  set local-preference 200\nrouter bgp 65000\n  neighbor {src_subnet} route-map PREFER_WIRED in"
           for _ in devices]
    return policy, cli


def drop_guest_weekend(vlan: str, devices: list) -> tuple[dict, list]:
    policy = {"type": "drop_guest_weekend", "vlan": vlan}
    cli = [f"time-range WEEKENDS\n  periodic weekend 00:00 to 23:59\nip access-list extended DROP_GUEST\n  deny ip {vlan} any time-range WEEKENDS\ninterface Vlan{vlan}\n  ip access-group DROP_GUEST in"
           for _ in devices]
    return policy, cli


def add_vlan(vlan_id: int, name: str, devices: list) -> tuple[dict, list]:
    policy = {"type": "add_vlan", "vlan_id": vlan_id, "name": name}
    cli = [f"vlan {vlan_id}\n  name {name}\ninterface range all\n  switchport trunk allowed vlan add {vlan_id}"
           for _ in devices]
    return policy, cli


ALL_POLICIES = [
    block_subnet, rate_limit, quarantine, voip_path, block_ip,
    temp_access, mirror_traffic, prefer_wired, drop_guest_weekend, add_vlan,
]
