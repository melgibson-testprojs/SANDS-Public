# risk/levels.py
from enum import Enum

class RiskLevel(Enum):
    CLEAN = "clean"
    WATCH = "watch"
    SUSPICIOUS = "suspicious"
    HIGH = "high"
    CRITICAL = "critical"


def score_to_level(score: float) -> RiskLevel:
    if score <= 20:
        return RiskLevel.CLEAN
    elif score <= 40:
        return RiskLevel.WATCH
    elif score <= 60:
        return RiskLevel.SUSPICIOUS
    elif score <= 80:
        return RiskLevel.HIGH
    else:
        return RiskLevel.CRITICAL
