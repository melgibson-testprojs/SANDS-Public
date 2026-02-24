import time
from agent.core.logger import get_logger
from agent.modes.agent_state import AgentState

logger = get_logger("base_agent")


class BaseAgent:
    def __init__(self, config, comm_http=None, comm_mqtt=None):
        self.config = config
        self.comm_http = comm_http
        self.comm_mqtt = comm_mqtt

        self.logger = get_logger(self.__class__.__name__)

        self.agent_id = config.agent_id
        self.token = config.token

        self.state = AgentState.INIT
        self.last_successful_contact = None

        # retry/backoff
        self._retry_backoff = 1.0
        self._retry_backoff_max = 30.0

    # ---------------- REGISTRATION ---------------- #

    def register(self):
        try:
            logger.info("Attempting registration with backend")

            resp = self.comm_http.register(
                agent_id=self.agent_id,
                capabilities=self.capabilities()
            )

            if isinstance(resp, dict):
                token = resp.get("token")
                if token:
                    self.token = token
                    self.comm_http.token = token
                    if self.comm_mqtt:
                        self.comm_mqtt.token = token

                self.model_version = resp.get("model_version", "base")
                self.model_path = resp.get("model_path")

                logger.info(f"MODEL_ASSIGNED | version={self.model_version}")

                self.state = AgentState.REGISTERED
                self.last_successful_contact = time.time()
                self._retry_backoff = 1.0

                logger.info("Agent registered successfully")
                return True

        except Exception as e:
            logger.warning(f"Registration failed: {e}")

        self._handle_backend_failure()
        return False

    # ---------------- HEARTBEAT ---------------- #

    def heartbeat(self):
        payload = {
            "agent_id": self.agent_id,
            "state": self.state.value,
            "ts": time.time()
        }

        try:
            self.comm_http.heartbeat(payload)

            self.last_successful_contact = time.time()

            if self.state != AgentState.REGISTERED:
                self.state = AgentState.REGISTERED
                logger.info("Backend reachable again → REGISTERED")

        except Exception:
            self._handle_backend_failure()

    # ---------------- TELEMETRY ---------------- #

    def send_telemetry(self, payload):
        try:
            resp = self.comm_http.send_telemetry(payload)
            self.last_successful_contact = time.time()
            return resp
        except Exception:
            self._handle_backend_failure()
            return None


    # ---------------- FAILURE HANDLING ---------------- #

    def _handle_backend_failure(self):
        now = time.time()

        if self.last_successful_contact:
            if now - self.last_successful_contact > 60:
                self.state = AgentState.OFFLINE
            else:
                self.state = AgentState.DEGRADED
        else:
            self.state = AgentState.DEGRADED

        logger.warning(f"Backend unreachable → state={self.state.value}")

        time.sleep(self._retry_backoff)
        self._retry_backoff = min(self._retry_backoff * 2, self._retry_backoff_max)

    # ---------------- CAPABILITIES ---------------- #

    def capabilities(self):
        return ["network"]

    def run(self):
        raise NotImplementedError("run() must be implemented by subclasses")