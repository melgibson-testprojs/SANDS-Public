import time
from typing import Dict

TOKEN_TTL = 60  # seconds

class PortalTokenStore:
    def __init__(self):
        self._tokens: Dict[str, dict] = {}

    def create(self, token: str, ip: str):
        self._tokens[token] = {
            "ip": ip,
            "ts": time.time()
        }

    def consume(self, token: str):
        data = self._tokens.pop(token, None)
        if not data:
            return None

        # TTL check
        if time.time() - data["ts"] > TOKEN_TTL:
            return None

        return data


portal_token_store = PortalTokenStore()
