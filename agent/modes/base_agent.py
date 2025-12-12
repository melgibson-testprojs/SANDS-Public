import time
from ..core.logger import get_logger

logger = get_logger("base_agent")


class BaseAgent:
    def __init__(self, config, comm_http=None, comm_mqtt=None):
        self.config = config
        self.comm_http = comm_http
        self.comm_mqtt = comm_mqtt
        self.agent_id = config.agent_id
        self.mode = "remote"
        self.token = config.token

    def register(self):
        try:
            resp = self.comm_http.register(self.agent_id, self.capabilities())
            if isinstance(resp, dict):
                token = resp.get("token") or resp.get("agent_token")
                if token:
                    self.token = token
                    self.comm_http.token = token
                    if self.comm_mqtt:
                        self.comm_mqtt.token = token
                logger.info(f"registered successfully (token received: {bool(token)})")
            return resp
        except Exception as e:
            logger.error(f"registration error: {e}")
            return None

    def capabilities(self):
        return ["network"]

    def heartbeat(self):
        payload = {"agent_id": self.agent_id, "ts": time.time(), "mode": self.mode}
        try:
            self.comm_http.heartbeat(payload)
        except Exception:
            if self.comm_mqtt:
                try:
                    self.comm_mqtt.publish(f"agents/{self.agent_id}/heartbeat", payload)
                except Exception:
                    logger.error("heartbeat failed via both http & mqtt")

    def send_telemetry(self, payload: dict):
        try:
            return self.comm_http.send_telemetry(payload)
        except Exception:
            if self.comm_mqtt:
                try:
                    self.comm_mqtt.publish(f"agents/{self.agent_id}/telemetry", payload)
                except Exception:
                    logger.error("telemetry failed via both http & mqtt")

    def run(self):
        raise NotImplementedError("Run loop must be implemented in subclass.")
