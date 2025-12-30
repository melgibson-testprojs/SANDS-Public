from typing import Dict

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

        if key not in self.devices:
            self.devices[key] = {
                "key": key,
                "agent_id": agent_id,
                "mac": mac,
                "ip": ip,
                "status": "online"
            }
        else:
            # update status / ip if changed
            self.devices[key]["status"] = "online"
            if ip:
                self.devices[key]["ip"] = ip

        return self.devices[key]

    def all(self):
        return list(self.devices.values())


device_store = DeviceStore()