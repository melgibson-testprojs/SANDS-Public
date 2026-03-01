from typing import Dict
import time

class DeviceStore:
    def __init__(self):
        self.devices: Dict[str, dict] = {}
        self.agents: Dict[str, dict] = {} # agent_id -> info

    def _make_key(self, mac=None):
        if not mac:
            raise ValueError("MAC is required for device identity")
        return f"mac:{mac.lower()}"


    def register(self, *, mac, ip=None, agent_id=None):
        key = self._make_key(mac)
        now = time.time()

        if agent_id:
            self.agents[agent_id] = {"id": agent_id, "last_seen": now, "ip": ip}

        if key not in self.devices:
            self.devices[key] = {
                "key": key,
                "mac": mac.lower(),
                "ip": ip,
                "agent_id": agent_id,
                "discoverers": [agent_id] if agent_id else [],
                "status": "online",
                "approved": False,
                "last_seen": now,
                "risk": 0.0
            }
        else:
            d = self.devices[key]
            d["last_seen"] = now
            if d.get("status") not in ("blocked", "quarantined"):
                d["status"] = "online"
            if ip:
                d["ip"] = ip
            if agent_id:
                d["agent_id"] = agent_id
                if "discoverers" not in d:
                    d["discoverers"] = []
                if agent_id not in d["discoverers"]:
                    d["discoverers"].append(agent_id)

        return self.devices[key]


    def heartbeat(self, agent_id: str, ip: str | None = None):
        now = time.time()
        self.agents[agent_id] = {"id": agent_id, "last_seen": now, "ip": ip}
        
        # Also find any device registered to this agent
        for d in self.devices.values():
            discoverers = d.get("discoverers", [])
            if d.get("agent_id") == agent_id or agent_id in discoverers:
                d["last_seen"] = now
                if d.get("status") not in ("blocked", "quarantined"):
                    d["status"] = "online"

    def all(self):
        now = time.time()
        for d in self.devices.values():
            age = now - d["last_seen"]
            if age > 90:
                d["status"] = "offline"
            elif age > 30:
                if d.get("status") not in ("blocked", "quarantined"):
                    d["status"] = "stale"
            else:
                if d.get("status") not in ("blocked", "quarantined"):
                    d["status"] = "online"
        return list(self.devices.values())

    def get(self, key: str):
        return self.devices.get(key)


device_store = DeviceStore()