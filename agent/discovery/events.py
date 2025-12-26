# agent/discovery/events.py

from dataclasses import dataclass
from typing import Optional
import time


@dataclass
class DeviceDiscoveredEvent:
    ip: str
    mac: str
    hostname: Optional[str] = None
    source: str = "unknown"   # dhcp / arp
    timestamp: float = time.time()