import time
from collections import defaultdict
from typing import Dict, List

class PredictionStore:
    def __init__(self):
        # device_key -> list of prediction events
        self._store: Dict[str, List[dict]] = defaultdict(list)

    def add(self, device_key: str, decision: str, score: float, source: str, extra: dict | None = None):
        self._store[device_key].append({
            "ts": time.time(),
            "decision": decision,
            "score": score,
            "source": source,
            "extra": extra or {}
        })

        # Keep last 50 only (SOC-friendly)
        self._store[device_key] = self._store[device_key][-50:]

    def get(self, device_key: str) -> List[dict]:
        return self._store.get(device_key, [])

prediction_store = PredictionStore()
