# agent/comm/swarm_protocol.py

from enum import Enum


# -----------------------------
# Topic helpers (NO folders)
# -----------------------------

class SwarmTopics:
    @staticmethod
    def logical_alerts(lid: str) -> str:
        return f"logical/{lid}/alerts"

    @staticmethod
    def logical_alerts_all() -> str:
        return "logical/+/alerts"

    @staticmethod
    def agent_commands(agent_id: str) -> str:
        return f"agent/{agent_id}/commands"

    GLOBAL_ALERTS = "global/alerts"


# -----------------------------
# Message types
# -----------------------------

class SwarmMsgType(str, Enum):
    WARN = "WARN"
    ESCALATE = "ESCALATE"
    CMD = "CMD"


class SwarmCode(str, Enum):
    ANOM_BEHAV = "ANOM_BEHAV"
    PORT_SCAN = "PORT_SCAN"
    BRUTE_FORCE = "BRUTE_FORCE"
    MAL_CONFIRMED = "MAL_CONFIRMED"
    QUARANTINE = "QUARANTINE"
