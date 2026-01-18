import threading
from enum import Enum
import time
from agent.core.logger import get_logger
from risk.engine import RiskEngine

logger = get_logger("logical_registry")

class DeviceState(Enum):
    NEW = "new"
    APPROVED = "approved"
    BLOCKED = "blocked"


class LogicalAgentRegistry:
    """
    SINGLE source of truth for device → logical agent mapping
    """

    def __init__(self, physical_agent_id: str):
        self.physical_agent_id = physical_agent_id
        self._lock = threading.Lock()

        self.devices = {}      # device_id -> metadata
        self.ip_index = {}     # ip -> device_id

    def register_device(self, device_id, ip, mac, hostname=None) -> bool:
        """
        Register a new logical agent if not already known.
        Returns True if created, False if already existed.
        """
        
        with self._lock:
            if device_id in self.devices:
                # IP may change over time
                self.ip_index[ip] = device_id
                return False

            logger.info(
                f"Registering logical agent | "
                f"device_id={device_id} ip={ip} mac={mac}"
            )
        
            self.devices[device_id] = {
                "ip": ip,
                "mac": mac,
                "hostname": hostname or "UNKNOWN",
                "state": DeviceState.NEW,

                # 🔐 Risk
                "risk": 0.0,
                "risk_engine": RiskEngine(),

                "flows": 0,
                "first_seen": time.time(),
            }


            self.ip_index[ip] = device_id
            return True

    

    def resolve_device(self, ip: str):
        """
        Resolve source IP → logical agent ID
        """
        return self.ip_index.get(ip)
    
    def get_device(self, device_id: str):
        return self.devices.get(device_id)


    def get_state(self, device_id: str):
        device = self.devices.get(device_id)
        return device["state"] if device else None


    def set_state(self, device_id: str, new_state: DeviceState):
        with self._lock:
            device = self.devices.get(device_id)

            if not device:
                logger.warning(
                    f"STATE_CHANGE_FAILED | unknown_device={device_id}"
                )
                return

            old_state = device["state"]

            if old_state == new_state:
                return  # no-op, avoids log spam

            device["state"] = new_state

            logger.info(
                "DEVICE_STATE_CHANGE | "
                f"device_id={device_id} | "
                f"ip={device['ip']} | "
                f"mac={device['mac']} | "
                f"{old_state.value} -> {new_state.value}"
            )


    
    
