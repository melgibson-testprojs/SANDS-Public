import requests
from ..core.logger import get_logger

logger = get_logger("http_client")


class HTTPClient:
    def __init__(self, server_url: str, token: str = None, timeout: int = 5):
        self.server = server_url.rstrip("/")
        self.token = token
        self.timeout = timeout

    def _headers(self):
        h = {"Content-Type": "application/json"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    def register(self, agent_id: str, capabilities: list):
        url = f"{self.server}/register"
        payload = {"agent_id": agent_id, "capabilities": capabilities}
        try:
            r = requests.post(url, json=payload, headers=self._headers(), timeout=self.timeout)
            r.raise_for_status()
            logger.info(f"register response: {r.status_code}")
            return r.json()
        except Exception as e:
            logger.error(f"register failed: {e}")
            raise

    def heartbeat(self, payload: dict):
        url = f"{self.server}/heartbeat"
        try:
            r = requests.post(url, json=payload, headers=self._headers(), timeout=self.timeout)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.error(f"heartbeat failed: {e}")
            raise

    def send_telemetry(self, payload: dict):
        url = f"{self.server}/telemetry"
        try:
            r = requests.post(url, json=payload, headers=self._headers(), timeout=self.timeout)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.error(f"telemetry failed: {e}")
            raise
    
    def post(self, path: str, payload: dict):
        url = f"{self.server}{path}"
        try:
            r = requests.post(
                url,
                json=payload,
                headers=self._headers(),
                timeout=self.timeout
            )
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.error(f"POST {path} failed: {e}")
            raise

    def get(self, path: str):
        """
        Generic GET request helper.
        """
        url = f"{self.server}{path}"
        try:
            r = requests.get(
                url,
                headers=self._headers(),
                timeout=self.timeout
            )
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.error(f"GET {path} failed: {e}")
            raise

