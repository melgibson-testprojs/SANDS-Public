from enum import Enum


class AgentState(Enum):
    INIT = "INIT"
    REGISTERED = "REGISTERED"
    DEGRADED = "DEGRADED"
    OFFLINE = "OFFLINE"