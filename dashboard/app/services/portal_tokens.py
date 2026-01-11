import time
from typing import Dict, List

TOKEN_TTL = 120  # seconds

class PortalTokenStore:
    def __init__(self):
        self._tokens: Dict[str, dict] = {}

    def create(self, token: str):
        self._tokens[token] = {
            "ts": time.time(),
            "used": False
        }

    def list_pending(self) -> List[str]:
        now = time.time()
        return [
            token
            for token, data in self._tokens.items()
            if not data["used"] and (now - data["ts"]) < TOKEN_TTL
        ]

    def consume(self, token: str):
        data = self._tokens.get(token)
        if not data:
            return None

        if data["used"]:
            return None

        if time.time() - data["ts"] > TOKEN_TTL:
            self._tokens.pop(token, None)
            return None

        data["used"] = True
        return data


portal_token_store = PortalTokenStore()
