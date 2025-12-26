import time
import hashlib
from dataclasses import dataclass, field


def generate_logical_agent_id(
    physical_agent_id: str,
    src_ip: str,
    mac: str | None = None
) -> str:
    base = f"{physical_agent_id}|{src_ip}|{mac or 'nomac'}"
    return hashlib.sha256(base.encode()).hexdigest()[:16]


@dataclass
class LogicalAgent:
    logical_agent_id: str
    src_ip: str
    mac: str | None

    first_seen: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)

    trust_score: float = 0.5
    anomaly_count: int = 0
    malicious_count: int = 0

    def update_last_seen(self):
        self.last_seen = time.time()
