from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Packet:
    src: str
    dst: str
    size_bytes: int
    sent_time: float
    received_time: Optional[float] = None
    path: List[str] = field(default_factory=list)
    flow_id: str = ""
    priority: int = 0                                                         
    dropped: bool = False

    def latency(self) -> Optional[float]:
        if self.received_time is None:
            return None
        return self.received_time - self.sent_time
