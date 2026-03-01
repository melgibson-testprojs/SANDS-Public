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
        new_state = payload["state"]
        if new_state in ("blocked", "quarantined"):
            device["status"] = new_state
            device["approved"] = False
        elif new_state == "approved":
            # Only allow setting back to approved if NOT already blocked by someone else
            if device.get("status") not in ("blocked", "quarantined"):
                device["status"] = "approved"
                device["approved"] = True

    # 🔥 THIS IS WHAT FIXES SOC RISK
    if "risk" in payload:
        device["risk"] = float(payload["risk"])

    device["last_seen"] = time.time()

    return {"status": "ok"}
