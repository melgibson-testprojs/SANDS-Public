import time
from risk.models import RiskEvent, RiskState
from risk import config
from agent.core.logger import get_logger
logger = get_logger("risk_engine")


class RiskEngine:
    def __init__(self):
        self.state = RiskState()

    def tick(self):
        self._decay()

    def _decay(self):
        now = time.time()
        dt = now - self.state.last_updated
        self.state.value = max(
            0.0,
            self.state.value - dt * config.DECAY_PER_SEC
        )
        self.state.last_updated = now

        #RISK DECAY LOG IF U WANT
        # logger.debug(
        #     f"RISK_DECAY | new_value={self.state.value:.2f}"
        # )


    def ingest(self, event: RiskEvent):
        self._decay()

        self.state.value += event.score
        self.state.value = min(self.state.value, config.MAX_RISK)
        self.state.history.append(event)

        logger.info(
            f"RISK_UPDATE | source={event.source} | "
            f"code={event.code} | "
            f"delta={event.score:.2f} | "
            f"total={self.state.value:.2f}"
        )


    def level(self) -> str:
        v = self.state.value
        if v >= config.BLOCK_THRESHOLD:
            return "CRITICAL"
        if v >= config.QUARANTINE_THRESHOLD:
            return "HIGH"
        if v >= 1.0:
            return "MED"
        return "LOW"

    def should_quarantine(self) -> bool:
        return self.state.value >= config.QUARANTINE_THRESHOLD

    def should_block(self) -> bool:
        return self.state.value >= config.BLOCK_THRESHOLD
    
    def reset(self):
        self.state.value = 0.0
