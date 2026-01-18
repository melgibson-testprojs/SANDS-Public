from fastapi import APIRouter
import time
from dashboard.app.services.device_store import device_store

router = APIRouter()

@router.post("/api/devices/state")
def update_device_state(payload: dict):
    """
    Called by agents to push:
    - state
    - risk
    - ip/mac
    """
    mac = payload.get("mac")
    if not mac:
        return {"status": "ignored", "reason": "missing mac"}

    device = device_store.register(
        mac=mac,
        ip=payload.get("ip"),
        agent_id=payload.get("agent_id")
    )

    # update state
    if "state" in payload:
        device["status"] = payload["state"]
        device["approved"] = payload["state"] == "approved"

    # 🔥 THIS IS WHAT FIXES SOC RISK
    if "risk" in payload:
        device["risk"] = float(payload["risk"])

    device["last_seen"] = time.time()

    return {"status": "ok"}
