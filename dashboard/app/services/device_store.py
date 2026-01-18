from typing import Dict
import time

class DeviceStore:
    def __init__(self):
        self.devices: Dict[str, dict] = {}

    def _make_key(self, mac=None):
        if not mac:
            raise ValueError("MAC is required for device identity")
        return f"mac:{mac.lower()}"


    def register(self, *, mac, ip=None, agent_id=None):
        key = self._make_key(mac)
        now = time.time()

        if key not in self.devices:
            self.devices[key] = {
                "key": key,
                "mac": mac.lower(),
                "ip": ip,
                "agent_id": agent_id,
                "status": "online",
                "approved": False,
                "last_seen": now,
                "risk": 0.0
            }
        else:
            d = self.devices[key]
            d["last_seen"] = now
            d["status"] = "online"
            if ip:
                d["ip"] = ip
            if agent_id:
                d["agent_id"] = agent_id

        return self.devices[key]


    def heartbeat(self, agent_id: str, ip: str | None = None):
        key = f"agent:{agent_id}"
        if key in self.devices:
            self.devices[key]["last_seen"] = time.time()
            self.devices[key]["status"] = "online"
            if ip:
                self.devices[key]["ip"] = ip

    def all(self):
        now = time.time()
        for d in self.devices.values():
            age = now - d["last_seen"]
            if age > 90:
                d["status"] = "offline"
            elif age > 30:
                d["status"] = "stale"
            else:
                d["status"] = "online"
        return list(self.devices.values())

    def get(self, key: str):
        return self.devices.get(key)


device_store = DeviceStore()