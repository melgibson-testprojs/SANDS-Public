from typing import Dict
import time

class DeviceStore:
    def __init__(self):
        self.devices: Dict[str, dict] = {}

    def _make_key(self, agent_id=None, mac=None, ip=None):
        if agent_id:
            return f"agent:{agent_id}"
        if mac:
            return f"mac:{mac}"
        return f"ip:{ip}"

    def register(self, *, agent_id=None, mac=None, ip=None):
        key = self._make_key(agent_id, mac, ip)
        now = time.time()

        if key not in self.devices:
            self.devices[key] = {
                "key": key,
                "agent_id": agent_id,
                "mac": mac,
                "ip": ip,
                "status": "online",
                "last_seen": now
            }
        else:
            self.devices[key]["last_seen"] = now
            self.devices[key]["status"] = "online"
            if ip:
                self.devices[key]["ip"] = ip

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