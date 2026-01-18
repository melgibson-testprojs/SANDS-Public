from dataclasses import dataclass, field
import time
from typing import List

@dataclass
class RiskEvent:
    source: str              # ml / swarm / behavior
    code: str                # ANOM_BEHAV, PORT_SCAN
    score: float             # normalized 0–1 or raw
    ts: float = field(default_factory=time.time)

@dataclass
class RiskState:
    value: float = 0.0
    last_updated: float = field(default_factory=time.time)
    history: List[RiskEvent] = field(default_factory=list)
